import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "牧場 作業ボード",
    short_name: "作業ボード",
    description: "声で話した作業が、誰が・何時に・何をしたか時系列で積まれていく記録ボード",
    start_url: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#f4efe4",
    theme_color: "#2f6b3a",
    lang: "ja",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
    ],
  };
}
