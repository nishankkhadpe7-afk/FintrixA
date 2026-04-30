export function getApiBaseUrl() {
  const configuredBaseUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "https://fintrixA.onrender.com"; // Fallback to production backend

  if (configuredBaseUrl && configuredBaseUrl !== "") {
    return configuredBaseUrl.replace(/\/$/, "");
  }

  return "https://fintrixA.onrender.com"; // Fallback
}
