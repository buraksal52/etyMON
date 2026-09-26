import { Suspense } from "react";

import AdminLoginForm from "./form";

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <main className="screen">
          <p>Loading login…</p>
        </main>
      }
    >
      <AdminLoginForm />
    </Suspense>
  );
}
