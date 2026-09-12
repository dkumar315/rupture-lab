export function BrandMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="1"
        y="1"
        width="30"
        height="30"
        rx="9"
        className="fill-zinc-950"
      />
      <path
        d="M6 17h5l2.2-6 4.1 12 2.4-6H26"
        className="stroke-emerald-400"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16.4 4.8 14.7 9l3.1 2.5-2.5 4.2"
        className="stroke-zinc-600"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
