// frontend/src/components/parcours/NextStepButton.tsx
import { Button } from "../ui/Button";

export function NextStepButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="text-right mt-5">
      <Button variant="primary" onClick={onClick} disabled={disabled}>
        {label} →
      </Button>
    </div>
  );
}
