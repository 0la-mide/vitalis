import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "VITALIS",
    short_name: "VITALIS",
    description: "Get to a hospital that is ready for you.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#046c4e",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
