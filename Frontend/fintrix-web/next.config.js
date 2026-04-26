/** @type {import('next').NextConfig} */
const nextConfig = {
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
