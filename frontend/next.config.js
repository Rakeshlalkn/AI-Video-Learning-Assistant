/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // `standalone` makes the production build self-contained — the Docker
  // image can copy just `.next/standalone` + a few static folders and run
  // `node server.js` with no node_modules. It also makes the dev experience
  // a tiny bit nicer since `next start` knows what to ship.
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:8000"}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
