import { Button } from "./Button";

interface EmptyProps {
  message: string;
  action?: { label: string; onClick: () => void };
}

export function Empty({ message, action }: EmptyProps) {
  return (
    <div className="state-block">
      <span>{message}</span>
      {action ? (
        <Button variant="ghost" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
