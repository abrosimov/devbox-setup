// Command ensures every line in targetLines is present in a text file.
//
// Template for ai_written_scripts/<slug>/main.go. Replace the planning,
// execution and verification bodies with the real task, keeping the shape:
// plan (pure, tested) -> print plan -> execute unless -dry-run -> verify.
//
// Run:  go run ./ai_written_scripts/<slug> [-dry-run] -file PATH
// Test: go test ./ai_written_scripts/<slug>
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"
	"strings"
)

var targetLines = []string{"example.setting = true"}

type step struct {
	description string
	line        string
}

// plan returns only the steps still needed, so a second run plans nothing.
func plan(current string, wanted []string) []step {
	present := lineSet(current)
	var steps []step
	for _, line := range wanted {
		if _, ok := present[line]; !ok {
			steps = append(steps, step{description: fmt.Sprintf("append %q", line), line: line})
		}
	}
	return steps
}

// verify returns the wanted lines that are still missing; empty means success.
func verify(current string, wanted []string) []string {
	present := lineSet(current)
	var missing []string
	for _, line := range wanted {
		if _, ok := present[line]; !ok {
			missing = append(missing, line)
		}
	}
	return missing
}

func lineSet(text string) map[string]struct{} {
	set := make(map[string]struct{})
	for _, line := range strings.Split(text, "\n") {
		set[line] = struct{}{}
	}
	return set
}

func execute(path, current string, steps []step) error {
	if len(steps) == 0 {
		return nil
	}
	var b strings.Builder
	b.WriteString(current)
	if current != "" && !strings.HasSuffix(current, "\n") {
		b.WriteString("\n")
	}
	for _, s := range steps {
		b.WriteString(s.line + "\n")
	}
	if err := os.WriteFile(path, []byte(b.String()), 0o644); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}

func readOptional(path string) (string, error) {
	data, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("reading %s: %w", path, err)
	}
	return string(data), nil
}

func run(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("script", flag.ContinueOnError)
	flags.SetOutput(stderr)
	path := flags.String("file", "", "file to update (required)")
	dryRun := flags.Bool("dry-run", false, "print the plan and change nothing")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if *path == "" {
		fmt.Fprintln(stderr, "-file is required")
		return 2
	}

	current, err := readOptional(*path)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	steps := plan(current, targetLines)

	if len(steps) == 0 {
		fmt.Fprintf(stdout, "nothing to do: %s is already up to date\n", *path)
	}
	prefix := ""
	if *dryRun {
		prefix = "would "
	}
	for _, s := range steps {
		fmt.Fprintf(stdout, "%s%s to %s\n", prefix, s.description, *path)
	}
	if *dryRun {
		return 0
	}

	if err := execute(*path, current, steps); err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}

	after, err := readOptional(*path)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	if missing := verify(after, targetLines); len(missing) > 0 {
		fmt.Fprintf(stderr, "VERIFY FAILED: still missing %q in %s\n", missing, *path)
		return 1
	}
	fmt.Fprintf(stdout, "VERIFY OK: %s contains all %d expected line(s)\n", *path, len(targetLines))
	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
