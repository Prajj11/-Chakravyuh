export function BrandMark({ large = false }: { large?: boolean }) {
  return (
    <svg
      className={large ? "brand-mark large" : "brand-mark"}
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="32"
        cy="32"
        r="27"
        stroke="currentColor"
        strokeOpacity=".22"
      />
      <circle
        cx="32"
        cy="32"
        r="20"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="86 40"
        transform="rotate(-65 32 32)"
      />
      <circle
        cx="32"
        cy="32"
        r="12"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="48 28"
        transform="rotate(30 32 32)"
      />
      <path
        d="M32 5v8M59 32h-8M32 59v-8M5 32h8"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle cx="32" cy="32" r="4" fill="currentColor" />
      <circle cx="49" cy="21" r="3" fill="currentColor" />
    </svg>
  );
}

export function SignalIllustration() {
  return (
    <div className="signal-illustration" aria-hidden="true">
      <svg viewBox="0 0 560 200" fill="none">
        <path
          d="M40 100H520M280 15V185"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="3 8"
        />
        {[45, 75, 105, 135].map((radius) => (
          <ellipse
            key={radius}
            cx="280"
            cy="100"
            rx={radius * 1.5}
            ry={radius * 0.62}
            stroke="currentColor"
            strokeOpacity=".13"
          />
        ))}
        <path
          d="M82 109L180 48L280 100L390 49L475 113M180 48L169 145L280 100L386 150L475 113M169 145L82 109M390 49L386 150"
          stroke="currentColor"
          strokeOpacity=".35"
        />
        {[
          [82, 109],
          [180, 48],
          [169, 145],
          [390, 49],
          [386, 150],
          [475, 113],
        ].map(([x, y], i) => (
          <g key={i}>
            <circle
              cx={x}
              cy={y}
              r="10"
              fill="#101a22"
              stroke="currentColor"
              strokeOpacity=".4"
            />
            <circle cx={x} cy={y} r="3" fill="currentColor" />
          </g>
        ))}
        <circle cx="280" cy="100" r="23" fill="#101a22" stroke="currentColor" />
        <circle cx="280" cy="100" r="7" fill="currentColor" />
      </svg>
      <div>
        <span>Observe the signal</span>
        <span>Connect the pattern</span>
        <span>Inspect the evidence</span>
      </div>
    </div>
  );
}
