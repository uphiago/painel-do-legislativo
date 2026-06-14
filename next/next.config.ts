import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "www.camara.leg.br" },
      { protocol: "https", hostname: "www25.senado.leg.br" },
      { protocol: "https", hostname: "www.senado.leg.br" },
    ],
  },
};

export default nextConfig;
