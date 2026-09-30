package main

import (
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestPlanListsOnlyMissingLines(t *testing.T) {
	tests := []struct {
		name    string
		current string
		want    []string
	}{
		{name: "empty file", current: "", want: []string{"a", "b"}},
		{name: "partly present", current: "a\n", want: []string{"b"}},
		{name: "complete", current: "a\nb\n", want: nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got []string
			for _, s := range plan(tt.current, []string{"a", "b"}) {
				got = append(got, s.line)
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("plan() lines = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestVerifyReportsMissingLines(t *testing.T) {
	if got := verify("a\n", []string{"a", "b"}); !reflect.DeepEqual(got, []string{"b"}) {
		t.Fatalf("verify() = %q, want [b]", got)
	}
	if got := verify("a\nb\n", []string{"a", "b"}); len(got) != 0 {
		t.Fatalf("verify() = %q, want none", got)
	}
}

func TestDryRunChangesNothing(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.txt")
	writeFile(t, path, "keep\n")

	if code := run([]string{"-dry-run", "-file", path}, io.Discard, io.Discard); code != 0 {
		t.Fatalf("run() exit = %d, want 0", code)
	}
	if got := readFile(t, path); got != "keep\n" {
		t.Fatalf("file changed on dry run: %q", got)
	}
}

func TestRunIsIdempotent(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.txt")
	writeFile(t, path, "keep")

	for i := range 2 {
		if code := run([]string{"-file", path}, io.Discard, io.Discard); code != 0 {
			t.Fatalf("run %d exit = %d, want 0", i+1, code)
		}
	}

	want := strings.Join(append([]string{"keep"}, targetLines...), "\n") + "\n"
	if got := readFile(t, path); got != want {
		t.Fatalf("file = %q, want %q", got, want)
	}
}

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(data)
}
