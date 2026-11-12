"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api, ApiError, type MeOut } from "@/lib/api";

export const HOSPITAL_ROLES = ["facility_admin", "receptionist", "nurse", "doctor", "lab"];

/** Where a signed-in account should land. */
export function homeFor(me: MeOut): string {
  if (me.status !== "approved") return "/auth/status";
  if (me.role === "network_admin") return "/admin";
  if (me.role === "worker") return "/worker";
  if (HOSPITAL_ROLES.includes(me.role) && me.facility?.status === "approved") return "/hospital";
  return "/auth/status";
}

/** Network admin pages: redirect anyone else. */
export function useRequireNetworkAdmin() {
  const router = useRouter();
  const q = useMe();
  useEffect(() => {
    if (q.error instanceof ApiError && q.error.status === 401) router.replace("/auth/login");
    if (q.data && (q.data.role !== "network_admin" || q.data.status !== "approved")) router.replace(homeFor(q.data));
  }, [q.data, q.error, router]);
  return q;
}

/** Frontline worker pages: approved workers only. */
export function useRequireWorker() {
  const router = useRouter();
  const q = useMe();
  useEffect(() => {
    if (q.error instanceof ApiError && q.error.status === 401) router.replace("/auth/login");
    if (q.data && (q.data.role !== "worker" || q.data.status !== "approved")) router.replace(homeFor(q.data));
  }, [q.data, q.error, router]);
  return q;
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<MeOut>("/auth/me"),
    retry: false,
  });
}

/** Redirects to login on 401, and to the status page if the account or facility is not verified. */
export function useRequireHospitalStaff() {
  const router = useRouter();
  const q = useMe();
  useEffect(() => {
    if (q.error instanceof ApiError && q.error.status === 401) router.replace("/auth/login");
    const me = q.data;
    if (!me) return;
    if (me.status !== "approved" || me.facility?.status !== "approved" || !HOSPITAL_ROLES.includes(me.role)) {
      router.replace("/auth/status");
    }
  }, [q.data, q.error, router]);
  return q;
}

export const ROLE_LABEL: Record<string, string> = {
  network_admin: "Network admin",
  facility_admin: "Facility admin",
  receptionist: "Receptionist",
  nurse: "Nurse",
  doctor: "Doctor",
  lab: "Lab / Radiology",
  worker: "Frontline worker",
};
