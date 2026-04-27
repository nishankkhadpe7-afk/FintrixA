/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendOrigin = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;

    if (!backendOrigin) {
      return [];
    }

    const normalizedOrigin = backendOrigin.replace(/\/$/, "");

    return [
      {
        source: "/api/:path*",
        destination: `${normalizedOrigin}/api/:path*`,
      },
    ];
  },

  webpack: (config, { dev }) => {
    // Avoid intermittent Windows filesystem cache corruption in dev mode.
    if (dev) {
      config.cache = {
        type: "memory",
      };
    }

    return config;
  },
};

module.exports = nextConfig;
