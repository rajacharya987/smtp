"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AliasesRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/forwarders/");
  }, [router]);
  return null;
}
