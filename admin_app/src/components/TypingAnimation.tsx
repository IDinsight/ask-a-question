/**
 * Three pulsing dots shown while waiting for a response.
 * Each dot starts a little later than the one before it.
 */
const TypingAnimation = () => {
  return (
    <div
      className="flex items-center gap-1 py-2"
      role="status"
      aria-label="Waiting for response"
    >
      {[0, 200, 400].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-pulse rounded-full bg-muted-foreground"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
};

export default TypingAnimation;
