"use client";

import dynamic from "next/dynamic";

const FarmMap = dynamic(() => import("@/components/FarmMap"), {
  ssr: false,
  loading: () => <p>Loading map…</p>,
});

export default function HomePage() {
  return (
    <main>
      <h1>FarmWise</h1>
      <p style={{ margin: "0.5rem 0 1rem" }}>
        Climate intelligence for smallholder farmers.
      </p>
      <FarmMap />
    </main>
  );
}
