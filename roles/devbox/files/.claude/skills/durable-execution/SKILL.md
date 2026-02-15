---
name: durable-execution
description: >
  Temporal workflow engine patterns and durable execution concepts. Covers workflow and activity
  design, determinism constraints, retry policies, signals, queries, child workflows, testing,
  and alternatives (Restate, Inngest). For Go and Python SDKs.
  Triggers on: Temporal, workflow, durable execution, activity, worker, saga orchestration,
  Restate, Inngest, Hatchet, workflow engine, replay, determinism.
---

# Durable Execution

Workflow engines that guarantee code runs to completion, surviving process crashes, deployments, and infrastructure failures.

---

## When to Use a Workflow Engine

| Situation | Use Workflow Engine? | Alternative |
|-----------|---------------------|-------------|
| Multi-step process with compensation | Yes | Saga with outbox (see `distributed-transactions`) |
| Long-running process (hours/days) | Yes | Risk of state loss with simple queues |
| Human-in-the-loop approval | Yes | Polling database is fragile |
| Simple async job (send email) | No | Background worker + outbox |
| Retry a single HTTP call | No | `tenacity`/`retry-go` (see `reliability-patterns`) |
| < 3 steps, no compensation | No | Transactional outbox is simpler |

**Rule of thumb:** If you're building a state machine with more than 3 states and need failure recovery, consider a workflow engine.

---

## Temporal Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Client App  │────→│  Temporal Server  │←────│  Worker Process │
│  (starter)   │     │  (orchestrator)   │     │  (executor)     │
└─────────────┘     └──────────────────┘     └────────────────┘
                           │                        │
                    Stores event history      Runs workflow &
                    Manages task queues       activity code
```

**Key concepts:**
- **Workflow**: deterministic orchestration function. Replayed from event history on recovery
- **Activity**: non-deterministic work (HTTP calls, DB writes, file I/O)
- **Task Queue**: named queue connecting starters to workers
- **Worker**: process that polls task queues and executes workflow/activity code
- **Signal**: external input to a running workflow
- **Query**: read-only inspection of workflow state

---

## Determinism: The Critical Constraint

Workflow code is **replayed** from event history to rebuild state. Non-deterministic code breaks replay.

### Forbidden in Workflow Code

| Forbidden | Why | Use Instead |
|-----------|-----|-------------|
| `time.Now()` / `datetime.now()` | Different on replay | `workflow.Now()` |
| `rand.Int()` / `random.randint()` | Different on replay | `workflow.SideEffect()` |
| HTTP calls, DB queries | Side effects re-execute | Activity |
| `os.Getenv()` | May change between replays | Pass as workflow input |
| Global mutable state | Shared across replays | Workflow-local variables |
| Goroutines / threads | Non-deterministic scheduling | `workflow.Go()` |
| `select` on channels | Non-deterministic | `workflow.Select()` |

### Go -- Workflow vs Activity Boundary

```go
// WORKFLOW -- deterministic orchestration only
func OrderWorkflow(ctx workflow.Context, order OrderInput) (OrderResult, error) {
    // Configure activity options
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval:    time.Second,
            BackoffCoefficient: 2.0,
            MaximumAttempts:    3,
        },
    })

    // Step 1: Reserve inventory (activity -- makes DB call)
    var inventoryResult InventoryResult
    if err := workflow.ExecuteActivity(actCtx, ReserveInventory, order).Get(ctx, &inventoryResult); err != nil {
        return OrderResult{}, fmt.Errorf("reserve inventory: %w", err)
    }

    // Step 2: Charge payment (activity -- makes HTTP call)
    var paymentResult PaymentResult
    if err := workflow.ExecuteActivity(actCtx, ChargePayment, order).Get(ctx, &paymentResult); err != nil {
        // Compensate: release inventory
        _ = workflow.ExecuteActivity(actCtx, ReleaseInventory, inventoryResult).Get(ctx, nil)
        return OrderResult{}, fmt.Errorf("charge payment: %w", err)
    }

    // Step 3: Ship (activity)
    var shipResult ShipmentResult
    if err := workflow.ExecuteActivity(actCtx, CreateShipment, order).Get(ctx, &shipResult); err != nil {
        _ = workflow.ExecuteActivity(actCtx, RefundPayment, paymentResult).Get(ctx, nil)
        _ = workflow.ExecuteActivity(actCtx, ReleaseInventory, inventoryResult).Get(ctx, nil)
        return OrderResult{}, fmt.Errorf("create shipment: %w", err)
    }

    return OrderResult{
        OrderID:    order.ID,
        PaymentID:  paymentResult.ID,
        ShipmentID: shipResult.ID,
    }, nil
}

// ACTIVITY -- non-deterministic work lives here
func ReserveInventory(ctx context.Context, order OrderInput) (InventoryResult, error) {
    // Safe: DB calls, HTTP calls, logging, time.Now() -- all fine here
    return inventoryService.Reserve(ctx, order.ItemID, order.Quantity)
}
```

### Python -- Workflow vs Activity Boundary

```python
from temporalio import workflow, activity
from datetime import timedelta

@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order: OrderInput) -> OrderResult:
        # Step 1: reserve inventory
        inventory = await workflow.execute_activity(
            reserve_inventory,
            order,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )

        # Step 2: charge payment
        try:
            payment = await workflow.execute_activity(
                charge_payment, order,
                start_to_close_timeout=timedelta(seconds=30),
            )
        except Exception:
            await workflow.execute_activity(release_inventory, inventory)
            raise

        return OrderResult(order_id=order.id, payment_id=payment.id)


@activity.defn
async def reserve_inventory(order: OrderInput) -> InventoryResult:
    # Safe: any I/O here
    return await inventory_service.reserve(order.item_id, order.quantity)
```

---

## Activity Best Practices

### Heartbeats for Long-Running Activities

If an activity takes more than a few seconds, use heartbeats to report progress and enable early cancellation detection.

```go
func ProcessLargeFile(ctx context.Context, fileURL string) error {
    reader, err := downloadFile(ctx, fileURL)
    if err != nil {
        return err
    }
    for i, chunk := range chunks(reader) {
        if err := processChunk(ctx, chunk); err != nil {
            return err
        }
        // Report progress; Temporal will retry from last heartbeat on failure
        activity.RecordHeartbeat(ctx, i)
    }
    return nil
}
```

### Activity Timeouts

| Timeout | Purpose | Typical Value |
|---------|---------|---------------|
| **ScheduleToStart** | Time in task queue waiting for a worker | 5 min (detect worker shortage) |
| **StartToClose** | Max execution time per attempt | 30s-5min depending on work |
| **ScheduleToClose** | Total time including retries | StartToClose * MaxAttempts |
| **Heartbeat** | Max time between heartbeats | 30s (detect stuck activities) |

---

## Signals and Queries

### Signals: Send Data to Running Workflow

```go
// Workflow: wait for approval signal
func ApprovalWorkflow(ctx workflow.Context, req ApprovalReq) error {
    var approved bool
    ch := workflow.GetSignalChannel(ctx, "approval")

    // Wait up to 24 hours for approval
    timerCtx, cancel := workflow.WithCancel(ctx)
    timer := workflow.NewTimer(timerCtx, 24*time.Hour)

    sel := workflow.NewSelector(ctx)
    sel.AddReceive(ch, func(c workflow.ReceiveChannel, more bool) {
        c.Receive(ctx, &approved)
        cancel() // cancel timer
    })
    sel.AddFuture(timer, func(f workflow.Future) {
        approved = false // timed out
    })
    sel.Select(ctx)

    if !approved {
        return ErrApprovalTimeout
    }
    return workflow.ExecuteActivity(ctx, ProcessApproved, req).Get(ctx, nil)
}

// Client: send the signal
client.SignalWorkflow(ctx, workflowID, "", "approval", true)
```

### Queries: Read Workflow State Without Side Effects

```go
func OrderWorkflow(ctx workflow.Context, order OrderInput) error {
    var status string
    // Register query handler
    _ = workflow.SetQueryHandler(ctx, "status", func() (string, error) {
        return status, nil
    })

    status = "reserving_inventory"
    // ... workflow steps, updating status as they complete
    status = "charging_payment"
    // ...
}

// Client: query the status
result, _ := client.QueryWorkflow(ctx, workflowID, "", "status")
```

---

## Versioning Workflow Code

When you need to change workflow logic for already-running workflows:

```go
func OrderWorkflow(ctx workflow.Context, order OrderInput) error {
    v := workflow.GetVersion(ctx, "add-fraud-check", workflow.DefaultVersion, 1)
    if v == 1 {
        // New code path: run fraud check before payment
        if err := workflow.ExecuteActivity(ctx, FraudCheck, order).Get(ctx, nil); err != nil {
            return err
        }
    }
    // Original code continues...
    return workflow.ExecuteActivity(ctx, ChargePayment, order).Get(ctx, nil)
}
```

---

## Testing Workflows

### Go -- Replay Test (Detect Non-Determinism)

```go
func TestOrderWorkflow_Replay(t *testing.T) {
    replayer := worker.NewWorkflowReplayer()
    replayer.RegisterWorkflow(OrderWorkflow)

    // Replay from a recorded history file
    err := replayer.ReplayWorkflowHistoryFromJSONFile(nil, "testdata/order_workflow_history.json")
    require.NoError(t, err)
}
```

### Go -- Unit Test with Mock Activities

```go
func TestOrderWorkflow(t *testing.T) {
    suite := testsuite.WorkflowTestSuite{}
    env := suite.NewTestWorkflowEnvironment()

    env.RegisterActivity(ReserveInventory)
    env.RegisterActivity(ChargePayment)

    env.OnActivity(ReserveInventory, mock.Anything, mock.Anything).
        Return(InventoryResult{ID: "inv-1"}, nil)
    env.OnActivity(ChargePayment, mock.Anything, mock.Anything).
        Return(PaymentResult{ID: "pay-1"}, nil)

    env.ExecuteWorkflow(OrderWorkflow, OrderInput{ID: "order-1"})

    require.True(t, env.IsWorkflowCompleted())
    require.NoError(t, env.GetWorkflowError())
}
```

### Go -- Static Analysis

```bash
# Detect non-deterministic code in workflows at build time
go install go.temporal.io/sdk/contrib/tools/workflowcheck@latest
workflowcheck ./...
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| **DB queries in workflow code** | Non-deterministic on replay | Move to activity |
| **No heartbeat on long activity** | Worker crash → restart from beginning | Add `activity.RecordHeartbeat()` |
| **Unbounded workflow history** | Memory + replay performance | Use `ContinueAsNew` for long loops |
| **Ignoring activity errors** | Silent failures | Always handle or propagate errors |
| **Large payloads in signals** | Bloats event history | Pass reference (ID), fetch in activity |
| **Non-idempotent activities** | Retry creates duplicates | Use idempotency keys |

### ContinueAsNew for Long-Running Workflows

```go
func PollingWorkflow(ctx workflow.Context) error {
    for i := 0; i < 1000; i++ { // process in batches
        if err := workflow.ExecuteActivity(ctx, PollAndProcess).Get(ctx, nil); err != nil {
            return err
        }
    }
    // Reset history to prevent unbounded growth
    return workflow.NewContinueAsNewError(ctx, PollingWorkflow)
}
```

---

## Alternatives Comparison

| Engine | Architecture | Best For | Trade-offs |
|--------|-------------|----------|------------|
| **Temporal** | External orchestrator, replay-based | Complex multi-service sagas | Separate server, learning curve |
| **Restate** | Embedded, virtual object model | Lightweight durable functions | Newer, smaller ecosystem |
| **Inngest** | Event-driven, step functions | Serverless workflows, simple DX | Less control over execution model |
| **AWS Step Functions** | Managed, JSON state machine | AWS-native workloads | Vendor lock-in, ASL syntax |

**Start with Temporal** if you need full control and have infrastructure capacity. Consider Inngest for simpler use cases where developer experience matters more.

> **See also:** `distributed-transactions` for outbox/saga without a workflow engine, `reliability-patterns` for retry/circuit breaker primitives, `transaction-safety` for local transaction boundaries.
