import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import type { RunNote } from "../types";
import { Button } from "./ui/Button";
import { useToast } from "../contexts/ToastContext";

/** Carnet d'un run : notes horodatées append-only (ajout + suppression). */
export function RunNotes({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [text, setText] = useState("");

  const notesQuery = useQuery({
    queryKey: queryKeys.runs.notes(runId),
    queryFn: () => apiFetch<RunNote[]>(`/api/runs/${encodeURIComponent(runId)}/notes`),
  });
  const notes = notesQuery.data ?? [];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.runs.notes(runId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.notes });
  };

  const addMutation = useMutation({
    mutationFn: (body: string) =>
      apiFetch(`/api/runs/${encodeURIComponent(runId)}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: body }),
      }),
    onSuccess: () => {
      setText("");
      invalidate();
      notify("Note ajoutée.", "success");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) =>
      apiFetch(`/api/runs/${encodeURIComponent(runId)}/notes/${encodeURIComponent(noteId)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      invalidate();
      notify("Note supprimée.", "success");
    },
  });

  const submit = () => {
    const t = text.trim();
    if (t) addMutation.mutate(t);
  };

  return (
    <div className="run-notes mt-4">
      <h4 style={{ margin: "0 0 var(--space-2)" }}>Carnet</h4>
      {notesQuery.isLoading ? (
        <p className="text-dim">Chargement des notes…</p>
      ) : notesQuery.error ? (
        <p className="text-dim">Notes indisponibles.</p>
      ) : notes.length === 0 ? (
        <p className="text-dim">Aucune note pour ce run.</p>
      ) : (
        <ul className="run-notes__list">
          {notes.map((n) => (
            <li key={n.id} className="run-notes__item">
              <span className="run-notes__ts text-dim">{new Date(n.ts).toLocaleString()}</span>
              <span className="run-notes__text">{n.text}</span>
              <Button
                variant="ghost"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(n.id)}
              >
                Supprimer
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="row mt-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Consigner une observation…"
          rows={2}
          aria-label="Nouvelle note"
          style={{
            flex: 1,
            padding: "var(--space-2)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-surface)",
            color: "var(--color-text)",
          }}
        />
        <Button variant="ghost" size="sm" disabled={!text.trim() || addMutation.isPending} onClick={submit}>
          Ajouter
        </Button>
      </div>
    </div>
  );
}
