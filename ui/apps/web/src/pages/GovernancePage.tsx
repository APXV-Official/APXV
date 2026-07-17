import {
  applyGovernanceProposal,
  approveGovernanceProposal,
  createGovernanceProposal,
  getGovernanceProposal,
  listGovernanceProposals,
  listGovernanceSpecs,
  rejectGovernanceProposal,
  type GovernanceProposal,
  type SpecType,
} from "@apxv/api-client";
import {
  ActionGroup,
  PageToolbar,
  Badge,
  Button,
  Alert,
  AlertDescription,
  DataSurface,
  EmptyState,
  Input,
  Label,
  SectionHeader,
  Select,
  Skeleton,
  StatusDot,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import {
  SelectableListBadge,
  SelectableListItem,
} from "../components/SelectableListItem";
import { LineDiffView } from "../components/LineDiffView";
import { formatApiError } from "../lib/api-errors";
import { MarkdownViewer } from "../components/MarkdownViewer";

const SPEC_TYPES: SpecType[] = ["rule", "workflow", "knowledge"];
const GOVERNANCE_TABS = ["specs", "proposals"] as const;
type GovernanceTab = (typeof GOVERNANCE_TABS)[number];

function proposalStatusVariant(
  status: string,
): "default" | "success" | "warning" | "destructive" | "secondary" {
  if (status === "applied") return "success";
  if (status === "approved") return "default";
  if (status === "proposed") return "warning";
  if (status === "rejected") return "destructive";
  return "secondary";
}

export function GovernancePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { proposal: proposalFromUrl, tab: tabParam } = useSearch({
    from: "/shell/governance",
  });
  const [activeTab, setActiveTab] = useState<GovernanceTab>(
    GOVERNANCE_TABS.includes(tabParam as GovernanceTab)
      ? (tabParam as GovernanceTab)
      : "specs",
  );
  const [activeSpec, setActiveSpec] = useState<SpecType>("rule");
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(
    proposalFromUrl ?? null,
  );

  useEffect(() => {
    if (tabParam && GOVERNANCE_TABS.includes(tabParam as GovernanceTab)) {
      setActiveTab(tabParam as GovernanceTab);
    }
  }, [tabParam]);

  useEffect(() => {
    setSelectedProposalId(proposalFromUrl ?? null);
  }, [proposalFromUrl]);

  function changeTab(tab: GovernanceTab) {
    setActiveTab(tab);
    void navigate({
      to: "/governance",
      search: {
        tab,
        proposal:
          tab === "proposals" ? (selectedProposalId ?? undefined) : undefined,
      },
    });
  }

  function selectProposal(id: string) {
    setSelectedProposalId(id);
    setActiveTab("proposals");
    void navigate({ to: "/governance", search: { tab: "proposals", proposal: id } });
  }

  const [editorSpecType, setEditorSpecType] = useState<SpecType>("rule");
  const [editorSummary, setEditorSummary] = useState("");
  const [editorContent, setEditorContent] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const specsQuery = useQuery({
    queryKey: ["governance", "specs"],
    queryFn: () => listGovernanceSpecs(),
  });

  const proposalsQuery = useQuery({
    queryKey: ["governance", "proposals"],
    queryFn: () => listGovernanceProposals(),
  });

  const proposalDetailQuery = useQuery({
    queryKey: ["governance", "proposal", selectedProposalId],
    queryFn: () => getGovernanceProposal(selectedProposalId!),
    enabled: Boolean(selectedProposalId),
  });

  const currentSpecContent =
    specsQuery.data?.specs?.[activeSpec]?.content ?? "";

  const currentForDiff = useMemo(() => {
    const specType = proposalDetailQuery.data?.proposal.spec_type;
    if (!specType) return "";
    return specsQuery.data?.specs?.[specType]?.content ?? "";
  }, [proposalDetailQuery.data, specsQuery.data]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["governance"] });
    void queryClient.invalidateQueries({ queryKey: ["health"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createGovernanceProposal({
        spec_type: editorSpecType,
        content: editorContent,
        summary: editorSummary,
        proposed_by: "operator-console",
      }),
    onSuccess: (data) => {
      invalidate();
      setShowCreate(false);
      if (data.proposal.id) selectProposal(data.proposal.id);
    },
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approveGovernanceProposal(id),
    onSuccess: invalidate,
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectGovernanceProposal(id, rejectReason),
    onSuccess: () => {
      setRejectReason("");
      invalidate();
    },
  });

  const applyMutation = useMutation({
    mutationFn: (id: string) => applyGovernanceProposal(id),
    onSuccess: invalidate,
  });

  const proposals = proposalsQuery.data?.proposals ?? [];
  const governanceStatus = specsQuery.data?.status as
    | { verification?: { valid?: boolean }; pending_proposals?: number }
    | undefined;

  function loadSpecIntoEditor(spec: SpecType) {
    const content = specsQuery.data?.specs?.[spec]?.content ?? "";
    setEditorSpecType(spec);
    setEditorContent(content);
    setEditorSummary(`Update ${spec} specification`);
    setShowCreate(true);
    changeTab("proposals");
  }

  return (
    <PageShell wide className="space-y-10">
      <PageToolbar>
        <span className="inline-flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[hsl(var(--muted-foreground))]">
          <span className="inline-flex items-center gap-2">
            <StatusDot
              tone={governanceStatus?.verification?.valid ? "success" : "warning"}
            />
            Specs {governanceStatus?.verification?.valid ? "approved" : "pending issues"}
          </span>
          {(governanceStatus?.pending_proposals ?? 0) > 0 && (
            <span>
              · {governanceStatus?.pending_proposals} pending proposal
              {(governanceStatus?.pending_proposals ?? 0) === 1 ? "" : "s"}
            </span>
          )}
        </span>
      </PageToolbar>

      <Tabs
        value={activeTab}
        onValueChange={(v) => changeTab(v as GovernanceTab)}
      >
        <TabsList>
          <TabsTrigger value="specs">Governance studio</TabsTrigger>
          <TabsTrigger value="proposals">
            Proposals ({proposals.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="specs" className="space-y-10 pt-6">
          <ActionGroup>
            {SPEC_TYPES.map((spec) => (
              <Button
                key={spec}
                variant="link"
                size="sm"
                className={[
                  "capitalize",
                  activeSpec === spec
                    ? "font-semibold underline"
                    : "font-normal text-[hsl(var(--muted-foreground))] no-underline hover:text-[hsl(var(--primary))]",
                ].join(" ")}
                onClick={() => setActiveSpec(spec)}
              >
                {spec}
              </Button>
            ))}
            <Button
              variant="link"
              size="sm"
              onClick={() => loadSpecIntoEditor(activeSpec)}
            >
              Propose change
            </Button>
          </ActionGroup>

          {specsQuery.isError && (
            <Alert variant="destructive">
              <AlertDescription>{formatApiError(specsQuery.error)}</AlertDescription>
            </Alert>
          )}

          {specsQuery.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : specsQuery.isError ? null : !currentSpecContent ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              No active {activeSpec} specification found.
            </p>
          ) : (
            <div className="max-h-[32rem] overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-5">
              <MarkdownViewer content={currentSpecContent} />
            </div>
          )}

          {specsQuery.data?.specs?.[activeSpec]?.hash && (
            <p className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
              Hash: {specsQuery.data.specs[activeSpec]?.hash}
            </p>
          )}
        </TabsContent>

        <TabsContent value="proposals" className="space-y-10 pt-6">
          <ActionGroup className="justify-end">
            <Button variant="link" size="sm" onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Cancel" : "New proposal"}
            </Button>
          </ActionGroup>

          {showCreate && (
            <section className="space-y-4 border-b border-[hsl(var(--divider))] pb-6">
              <SectionHeader title="Create proposal" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Submit a markdown spec change for approval.
              </p>
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label>Spec type</Label>
                  <Select
                    className="w-full capitalize"
                    value={editorSpecType}
                    onChange={(e) =>
                      setEditorSpecType(e.target.value as SpecType)
                    }
                  >
                    {SPEC_TYPES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Summary</Label>
                  <Input
                    value={editorSummary}
                    onChange={(e) => setEditorSummary(e.target.value)}
                    placeholder="Brief description of the change"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Proposed content (markdown)</Label>
                  <Textarea
                    rows={14}
                    value={editorContent}
                    onChange={(e) => setEditorContent(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <ActionGroup>
                  <Button
                    onClick={() => createMutation.mutate()}
                    disabled={createMutation.isPending || !editorContent.trim()}
                  >
                    {createMutation.isPending ? "Submitting…" : "Submit proposal"}
                  </Button>
                </ActionGroup>
                {createMutation.isError && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      {formatApiError(createMutation.error)}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </section>
          )}

          <div className="grid min-w-0 gap-8 xl:grid-cols-2 xl:gap-10">
            <section className="min-w-0 space-y-4">
              <SectionHeader title="Proposal queue" />
              <DataSurface>
                {proposals.length === 0 ? (
                  <EmptyState
                    title="No proposals yet"
                    description="Propose a spec change to start the governance workflow."
                  />
                ) : (
                  <div className="divide-y divide-[hsl(var(--divider-subtle))]">
                    {proposals.map((p: GovernanceProposal) => (
                      <SelectableListItem
                        key={p.id}
                        selected={selectedProposalId === p.id}
                        onClick={() => p.id && selectProposal(p.id)}
                        title={p.summary || p.id || "Proposal"}
                        subtitle={p.id}
                        badge={
                          <SelectableListBadge
                            variant={proposalStatusVariant(p.status)}
                          >
                            {p.status}
                          </SelectableListBadge>
                        }
                        meta={p.spec_type}
                      />
                    ))}
                  </div>
                )}
              </DataSurface>
            </section>

            <section className="min-w-0 space-y-4 border-t border-[hsl(var(--divider))] pt-6 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0">
              <SectionHeader
                title="Proposal detail"
                action={
                  selectedProposalId ? (
                    <span
                      className="max-w-[14rem] truncate font-mono text-sm text-[hsl(var(--muted-foreground))] sm:max-w-xs"
                      title={selectedProposalId}
                    >
                      {selectedProposalId}
                    </span>
                  ) : undefined
                }
              />

              {!selectedProposalId && (
                <EmptyState
                  title="No proposal selected"
                  description="Choose a proposal from the queue to review changes."
                />
              )}

              {selectedProposalId && proposalDetailQuery.isLoading && (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-40 w-full" />
                </div>
              )}

              {selectedProposalId && proposalDetailQuery.isError && (
                <Alert variant="destructive">
                  <AlertDescription className="space-y-3">
                    <p>{formatApiError(proposalDetailQuery.error)}</p>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0"
                      onClick={() =>
                        void navigate({
                          to: "/governance",
                          search: { tab: "proposals", proposal: undefined },
                        })
                      }
                    >
                      Clear selection
                    </Button>
                  </AlertDescription>
                </Alert>
              )}

              {proposalDetailQuery.data && (
                <>
                  <ActionGroup>
                    <Badge
                      variant={proposalStatusVariant(
                        proposalDetailQuery.data.proposal.status,
                      )}
                      className="capitalize"
                    >
                      {proposalDetailQuery.data.proposal.status}
                    </Badge>
                    <Badge variant="secondary" className="capitalize">
                      {proposalDetailQuery.data.proposal.spec_type}
                    </Badge>
                  </ActionGroup>

                  <LineDiffView
                    before={currentForDiff}
                    after={proposalDetailQuery.data.content}
                  />

                  <div className="max-h-48 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4">
                    <MarkdownViewer content={proposalDetailQuery.data.content} />
                  </div>

                  {proposalDetailQuery.data.proposal.status === "proposed" && (
                    <div className="space-y-4">
                      <ActionGroup>
                        <Button
                          size="sm"
                          disabled={approveMutation.isPending}
                          onClick={() => approveMutation.mutate(selectedProposalId!)}
                        >
                          Approve
                        </Button>
                      </ActionGroup>
                      <ActionGroup className="items-end">
                        <Input
                          placeholder="Rejection reason"
                          value={rejectReason}
                          onChange={(e) => setRejectReason(e.target.value)}
                          className="min-w-[12rem] flex-1"
                        />
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={rejectMutation.isPending}
                          onClick={() => rejectMutation.mutate(selectedProposalId!)}
                        >
                          Reject
                        </Button>
                      </ActionGroup>
                    </div>
                  )}

                  {proposalDetailQuery.data.proposal.status === "approved" && (
                    <ActionGroup>
                      <Button
                        size="sm"
                        disabled={applyMutation.isPending}
                        onClick={() => applyMutation.mutate(selectedProposalId!)}
                      >
                        Apply to active specs
                      </Button>
                    </ActionGroup>
                  )}

                  {(approveMutation.isError ||
                    rejectMutation.isError ||
                    applyMutation.isError) && (
                    <Alert variant="destructive">
                      <AlertDescription>
                        {formatApiError(
                          approveMutation.error ??
                            rejectMutation.error ??
                            applyMutation.error,
                        )}
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </section>
          </div>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}