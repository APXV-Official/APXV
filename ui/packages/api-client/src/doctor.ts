import { apiFetch } from "./http";
import type { DoctorResponse } from "./types";

export async function getSystemDoctor(checkLlm = false): Promise<DoctorResponse> {
  const query = checkLlm ? "?check_llm=true" : "";
  return apiFetch<DoctorResponse>(`/api/v2/system/doctor${query}`);
}