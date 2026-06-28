import { Suspense } from "react";
import JoinClient from "./join-client";

export default function JoinPage() {
  return (
    <Suspense fallback={<div className="page" />}>
      <JoinClient />
    </Suspense>
  );
}
