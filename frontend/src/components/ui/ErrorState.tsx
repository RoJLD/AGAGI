import { ApiError } from "../../api/client";
import { Button } from "./Button";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError
      ? `${error.status || "réseau"} sur ${error.endpoint} — ${error.message}`
      : error instanceof Error
        ? error.message
        : String(error);

  return (
    <div className="state-block error-state" role="alert">
      <strong>Erreur de chargement</strong>
      <span className="error-detail">{message}</span>
      {onRetry ? (
        <Button variant="ghost" size="sm" onClick={onRetry}>
          Réessayer
        </Button>
      ) : null}
    </div>
  );
}
