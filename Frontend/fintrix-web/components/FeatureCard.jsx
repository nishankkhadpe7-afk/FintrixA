import Link from "next/link";

const iconMap = {
  spark: {
    light: ["/ai-agent-logo-lightpng.png", "/ai-agent-logo.png"],
    dark: ["/ai-agent-logo.png"],
  },
  branch: {
    light: ["/what-if-logo-light.png", "/what-if-logo.png"],
    dark: ["/what-if-logo.png"],
  },
  chart: {
    light: ["/evaluation-logo-light.png", "/evaluation-logo.png"],
    dark: ["/evaluation-logo.png"],
  },
};

export default function FeatureCard({ title, description, icon, href, darkMode = false }) {
  const iconSet = iconMap[icon];
  const iconCandidates = darkMode ? iconSet?.dark || [] : iconSet?.light || [];
  const iconSrc = iconCandidates[0] || "";

  return (
    <Link
      href={href}
      className="group flex h-full min-h-[205px] flex-col items-start gap-4 rounded-[20px] border border-fintrix-dark/10 bg-white p-6 shadow-[0_12px_24px_rgba(5,47,95,0.15)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_18px_30px_rgba(5,47,95,0.2)] sm:flex-row sm:gap-6 sm:p-7"
    >
      <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full shadow-soft sm:h-[62px] sm:w-[62px]">
        {iconSrc ? (
          <img
            src={iconSrc}
            alt={`${title} logo`}
            className="h-full w-full object-cover"
            onError={(event) => {
              const currentIndex = iconCandidates.findIndex((candidate) => event.currentTarget.src.endsWith(candidate));
              const nextSrc = iconCandidates[currentIndex + 1];
              if (!nextSrc) return;
              event.currentTarget.src = nextSrc;
            }}
          />
        ) : null}
      </div>

      <div className="flex-1">
        <h3 className="text-2xl font-semibold tracking-[-0.03em] text-fintrix-ink transition-colors duration-300 group-hover:text-fintrix-dark sm:text-[30px]">
          {title}
        </h3>

        <p className="mt-2 text-base font-semibold leading-7 text-fintrix-muted sm:text-lg sm:leading-8">
          {description}
        </p>
      </div>
    </Link>
  );
}
