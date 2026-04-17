type EmptyStateProps = {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ message, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p>{message}</p>
      {actionLabel && onAction ? <button onClick={onAction}>{actionLabel}</button> : null}
    </div>
  );
}
