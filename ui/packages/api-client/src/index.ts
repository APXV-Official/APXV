export { createApxvClient } from "./config";
export type { ApxvClient } from "./config";

export {
  configureApi,
  getApiConfig,
  setUnauthorizedHandler,
  normalizeOperatorApiKey,
  isValidOperatorApiKey,
} from "./configure";
export type { ApiConfig } from "./configure";

export { ApiError, apiFetch } from "./http";
export type { ApiFetchOptions } from "./http";

export type {
  HealthResponse,
  IntegrityResult,
  DoctorResponse,
  DoctorCheck,
  ErrorEnvelope,
} from "./types";

export { getHealthLegacy, getSystemHealth, testApiConnection } from "./health";
export { getOperatorKeyHint } from "./operator-key";
export type { OperatorKeyHint } from "./operator-key";
export { getSystemDoctor } from "./doctor";
export { repairAuditLogs } from "./repair-audit";
export type { AuditRepairResult } from "./repair-audit";
export { getSystemStatus } from "./status";
export type { RuntimeStatus } from "./status";

export { listJobs, getJob } from "./jobs";
export type { Job, JobListResponse } from "./jobs";

export { runPipeline } from "./pipeline";
export type {
  PipelineRunRequest,
  PipelineRunResponse,
  JobQueued,
  PipelineRunResult,
} from "./pipeline";

export {
  listPipelines,
  getPipeline,
  savePipeline,
  validatePipeline,
  importPipeline,
  exportPipeline,
  deletePipeline,
  listPipelineTemplates,
  getPipelineTemplate,
  runCompositionPipeline,
} from "./pipelines";
export type {
  PipelineDocument,
  PipelineStep,
  PipelineEdge,
  PipelineListItem,
  PipelineTemplateInfo,
  PipelineRunTrace,
  RunTraceStep,
} from "./pipelines";

export {
  listArtifacts,
  getArtifact,
  getArtifactSummary,
} from "./artifacts";
export type {
  ArtifactRow,
  ArtifactListPage,
  ArtifactSummary,
} from "./artifacts";

export {
  listStudioAgents,
  saveStudioAgent,
  getStudioAgent,
  testStudioAgent,
  promoteStudioAgent,
  listStudioPacks,
  saveStudioPack,
  getStudioPack,
  testStudioPack,
  promoteStudioPack,
  getStudioShelf,
  listStudioProofs,
  listProofCatalog,
  listProofTemplates,
  saveStudioProof,
  saveStudioProofFromTemplate,
  getStudioProof,
  testStudioProof,
  promoteStudioProof,
  getProofStudioStatus,
  compileProofIntent,
  saveStudioProofFromIntent,
  exportProofClaim,
} from "./studio";
export type {
  StudioAgent,
  StudioPack,
  StudioProof,
  ProofPredicate,
  ProofTemplate,
} from "./studio";

export {
  activatePack,
  clonePack,
  createPack,
  getActivePack,
  getPack,
  listPacks,
} from "./packs";
export type {
  ActivatePackRequest,
  ActivatePackResponse,
  ActivePackRecord,
  ActivePackResponse,
  ClonePackRequest,
  ClonePackResponse,
  CreatePackRequest,
  CreatePackResponse,
  PackInfo,
} from "./packs";

export { getAgent, getPackAgents, listAgents } from "./agents";
export type {
  AgentInfo,
  AgentListResponse,
  PackAgentChain,
} from "./agents";

export { createUpload } from "./uploads";
export type { UploadSession, UploadFileInfo } from "./uploads";

export { getOllamaStatus } from "./integrations";
export type { OllamaStatus } from "./integrations";
export { repairIntegrations } from "./repair-integrations";
export type { IntegrationRepairResult } from "./repair-integrations";

export { streamJobs } from "./jobs-stream";
export type { JobStreamEvent } from "./jobs-stream";

export { listAuditLogs, getAuditEntries } from "./audit";
export type {
  AuditLogInfo,
  AuditEntry,
  AuditEntriesPage,
} from "./audit";

export {
  listGovernanceSpecs,
  listGovernanceProposals,
  getGovernanceProposal,
  createGovernanceProposal,
  approveGovernanceProposal,
  rejectGovernanceProposal,
  applyGovernanceProposal,
} from "./governance";
export type {
  SpecType,
  GovernanceSpec,
  GovernanceSpecsResponse,
  GovernanceProposal,
  GovernanceProposalDetail,
} from "./governance";

export { listBackups, createBackup, restoreBackup } from "./backups";
export type { BackupInfo } from "./backups";

export { listApiKeys, createApiKey, revokeApiKey } from "./keys";
export type { ApiKeyMeta, ApiKeyCreated } from "./keys";

export { getCapabilities } from "./capabilities";

export { runIntegrityCheck, getVerifierBundle } from "./system";
export type { VerifierBundleExport } from "./system";

export { verifyAttestation } from "./verify";
export type {
  VerificationReport,
  PythonVerification,
  PythonCheck,
  ZkCircuitReport,
} from "./verify";

export * from "./generated";