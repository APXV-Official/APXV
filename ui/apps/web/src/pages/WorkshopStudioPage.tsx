/**
 * APXV Workbench — freeform visual composition.
 * Drag building blocks, place them anywhere, wire ports like cables.
 */
import {
  getJob,
  getPipeline,
  getPipelineTemplate,
  getStudioShelf,
  listAgents,
  listPacks,
  listPipelines,
  listPipelineTemplates,
  runCompositionPipeline,
  savePipeline,
  type PipelineDocument,
  type PipelineEdge,
  type PipelineStep,
  type RunTraceStep,
} from "@apxv/api-client";
import {
  Alert,
  AlertDescription,
  Button,
  Checkbox,
  Input,
  Textarea,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useBlocker, useNavigate, useSearch } from "@tanstack/react-router";
import {
  Bot,
  Download,
  Layers,
  Package,
  Pause,
  Play,
  Plus,
  Power,
  Save,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";
import {
  llmPayloadFromPrefs,
  loadLastPipelineId,
  loadModelsPrefs,
  modeLabel,
  rememberLastPipelineId,
} from "../lib/models-prefs";
import {
  downloadText,
  emptyPipeline,
  kindLabel,
  maturityForUses,
  paletteFromCatalog,
  pipelineRefBlock,
  purposeForBlock,
  SAMPLE_PIPELINE_INPUT,
  stepFromBlock,
  syncAttachedPacks,
  usesKind,
  validateCompositionForRun,
  type MaturityLabel,
  type PaletteBlock,
  type ShelfCategory,
} from "../lib/workshop-pipeline";

type LiveStatus = Record<string, string>;
type StepMini = Record<string, string>;

const NODE_W = 176;
const NODE_H = 108;

function blockIcon(kind: string) {
  if (kind === "pack") return Package;
  if (kind === "control") return Zap;
  return Bot;
}

function statusRing(status?: string, off?: boolean): string {
  if (off) return "opacity-45 border-zinc-600";
  switch (status) {
    case "succeeded":
      return "border-emerald-400 shadow-[0_0_20px_rgba(52,211,153,0.35)]";
    case "failed":
      return "border-red-400 shadow-[0_0_20px_rgba(248,113,113,0.35)]";
    case "running":
      return "border-sky-400 shadow-[0_0_24px_rgba(56,189,253,0.45)] animate-pulse";
    case "awaiting_approval":
      return "border-amber-400 shadow-[0_0_20px_rgba(251,191,36,0.4)]";
    case "skipped":
      return "opacity-40 border-zinc-600";
    default:
      return "border-zinc-500/60";
  }
}

function kindTint(kind: string): string {
  if (kind === "pack") return "bg-violet-500/15";
  if (kind === "control") return "bg-amber-500/15";
  return "bg-cyan-500/15";
}

function edgeId(from: string, to: string, kind: string) {
  return `${from}->${to}:${kind}`;
}

function ensureLayout(step: PipelineStep, index: number): { x: number; y: number } {
  const x = step.layout?.x;
  const y = step.layout?.y;
  if (typeof x === "number" && typeof y === "number") return { x, y };
  return { x: 80 + index * 220, y: 140 + (index % 2) * 40 };
}

function maturityBadgeClass(m: MaturityLabel): string {
  if (m === "Official") return "bg-emerald-500/20 text-emerald-200";
  if (m === "Core") return "bg-cyan-500/20 text-cyan-200";
  return "bg-zinc-500/25 text-zinc-300";
}

export function WorkshopStudioPage() {
  const { id: searchId, shelf: shelfSearch } = useSearch({
    from: "/shell/workshop",
  });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const boardRef = useRef<HTMLDivElement>(null);
  const panRef = useRef({ x: 40, y: 40 });

  const [doc, setDoc] = useState<PipelineDocument>(() => emptyPipeline());
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null);
  const [inputText, setInputText] = useState(SAMPLE_PIPELINE_INPUT);
  const [live, setLive] = useState<LiveStatus>({});
  const [mini, setMini] = useState<StepMini>({});
  const [runBanner, setRunBanner] = useState<string | null>(null);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  // Auto-dismiss transient status banners (bind/save/load) so they never cover Run
  useEffect(() => {
    if (!runBanner) return;
    if (/running|queued|paused|finished|failed/i.test(runBanner)) return;
    const t = window.setTimeout(() => setRunBanner(null), 4500);
    return () => window.clearTimeout(t);
  }, [runBanner]);
  const [boardErrors, setBoardErrors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [shelfTab, setShelfTab] = useState<ShelfCategory>(() => {
    if (
      shelfSearch === "agents" ||
      shelfSearch === "packs" ||
      shelfSearch === "proofs" ||
      shelfSearch === "controls" ||
      shelfSearch === "library"
    ) {
      return shelfSearch;
    }
    return "agents";
  });
  const [shelfQuery, setShelfQuery] = useState("");
  const [sheetBlock, setSheetBlock] = useState<PaletteBlock | null>(null);
  const [hoverTip, setHoverTip] = useState<{
    stepId: string;
    x: number;
    y: number;
  } | null>(null);
  const [sessionRestored, setSessionRestored] = useState(false);
  /** Soft notice when we auto-opened last board from localStorage */
  const [restoredFromSession, setRestoredFromSession] = useState<string | null>(
    null,
  );

  // Canvas pan (move the board world inside a fixed viewport)
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const [panning, setPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const spaceDown = useRef(false);

  // Resizable inspector (right)
  const [inspectorW, setInspectorW] = useState(() => {
    try {
      const n = Number(localStorage.getItem("apxv.inspectorWidth"));
      if (Number.isFinite(n) && n >= 220 && n <= 640) return n;
    } catch {
      /* ignore */
    }
    // Match shelf default for visual balance; user can still drag wider
    return 260;
  });
  const [resizingInspector, setResizingInspector] = useState(false);
  const resizeStart = useRef({ x: 0, w: 0, kind: "" as "" | "inspector" | "shelf" });

  // Resizable shelf (left of board)
  const [shelfW, setShelfW] = useState(() => {
    try {
      const n = Number(localStorage.getItem("apxv.shelfWidth"));
      if (Number.isFinite(n) && n >= 180 && n <= 420) return n;
    } catch {
      /* ignore */
    }
    return 260;
  });
  const [resizingShelf, setResizingShelf] = useState(false);

  // Node drag
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  // Wire drag from output port (port: out | out2 | fail)
  const [wiringFrom, setWiringFrom] = useState<string | null>(null);
  const [wiringPort, setWiringPort] = useState<string>("out");

  useEffect(() => {
    panRef.current = pan;
  }, [pan]);

  useEffect(() => {
    try {
      localStorage.setItem("apxv.inspectorWidth", String(inspectorW));
    } catch {
      /* ignore */
    }
  }, [inspectorW]);

  useEffect(() => {
    try {
      localStorage.setItem("apxv.shelfWidth", String(shelfW));
    } catch {
      /* ignore */
    }
  }, [shelfW]);
  const [wirePos, setWirePos] = useState<{ x: number; y: number } | null>(null);

  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;

  useBlocker({
    shouldBlockFn: () => {
      if (!dirtyRef.current) return false;
      return !window.confirm(
        "You have unsaved board changes. Leave without saving? Your composition file on disk is unchanged until you Save.",
      );
    },
    enableBeforeUnload: dirty,
    withResolver: false,
  });

  const pipelinesQuery = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => listPipelines(),
  });
  const agentsQuery = useQuery({
    queryKey: ["agents", "studio"],
    queryFn: () => listAgents({ limit: 100 }),
  });
  const packsQuery = useQuery({
    queryKey: ["packs", "studio"],
    queryFn: () => listPacks(),
  });
  const studioShelfQuery = useQuery({
    queryKey: ["studio", "shelf"],
    queryFn: () => getStudioShelf(),
  });
  const templatesQuery = useQuery({
    queryKey: ["pipelines", "templates"],
    queryFn: () => listPipelineTemplates(),
  });
  const loadQuery = useQuery({
    queryKey: ["pipelines", "detail", searchId],
    queryFn: () => getPipeline(searchId!),
    enabled: Boolean(searchId),
  });

  useEffect(() => {
    if (
      shelfSearch === "agents" ||
      shelfSearch === "packs" ||
      shelfSearch === "proofs" ||
      shelfSearch === "controls" ||
      shelfSearch === "library"
    ) {
      setShelfTab(shelfSearch);
    }
  }, [shelfSearch]);

  // Session restore last pipeline when opening Workshop without id
  useEffect(() => {
    if (sessionRestored || searchId) {
      setSessionRestored(true);
      return;
    }
    const last = loadLastPipelineId();
    if (last) {
      setRestoredFromSession(last);
      void navigate({
        to: "/workshop",
        search: { id: last, shelf: shelfSearch },
        replace: true,
      });
    }
    setSessionRestored(true);
  }, [searchId, sessionRestored, navigate, shelfSearch]);

  useEffect(() => {
    if (searchId) rememberLastPipelineId(searchId);
  }, [searchId]);

  useEffect(() => {
    if (loadQuery.data?.pipeline) {
      const p = loadQuery.data.pipeline;
      // Ensure every step has layout for freeform board
      const steps = p.steps.map((s, i) => ({
        ...s,
        layout: ensureLayout(s, i),
        enabled: s.enabled !== false,
      }));
      setDoc({ ...p, steps, edges: p.edges ?? [] });
      setDirty(false);
      setSelectedStepId(steps[0]?.id ?? null);
      setLive({});
      setRunBanner(null);
      rememberLastPipelineId(p.id);
    }
  }, [loadQuery.data]);

  const palette = useMemo(() => {
    const coreAgents = agentsQuery.data?.items ?? [];
    const corePacks = packsQuery.data?.packs ?? [];
    const promotedAgents = (studioShelfQuery.data?.agents ?? []).map((a) => ({
      id: a.id,
      name: a.name,
      agent_type: a.agent_type,
      description: a.description,
    }));
    const promotedPacks = (studioShelfQuery.data?.packs ?? []).map((p) => ({
      id: p.id,
      name: p.name,
      description: p.description,
    }));
    const agentMap = new Map<string, (typeof coreAgents)[0]>();
    for (const a of [...coreAgents, ...promotedAgents]) {
      if (a.id) agentMap.set(a.id, a as (typeof coreAgents)[0]);
    }
    const packMap = new Map<string, (typeof corePacks)[0]>();
    for (const p of [...corePacks, ...promotedPacks]) {
      if (p.id) packMap.set(p.id, p as (typeof corePacks)[0]);
    }
    return paletteFromCatalog(
      Array.from(agentMap.values()),
      Array.from(packMap.values()),
    );
  }, [agentsQuery.data, packsQuery.data, studioShelfQuery.data]);

  const promotedProofs = studioShelfQuery.data?.proofs ?? [];

  const shelfItems = useMemo(() => {
    const q = shelfQuery.trim().toLowerCase();
    const match = (b: PaletteBlock) =>
      !q ||
      b.title.toLowerCase().includes(q) ||
      b.uses.toLowerCase().includes(q) ||
      b.subtitle.toLowerCase().includes(q);
    if (shelfTab === "agents") {
      return palette.filter((b) => b.kind === "agent" && match(b));
    }
    if (shelfTab === "packs") {
      return palette.filter((b) => b.kind === "pack" && match(b));
    }
    if (shelfTab === "proofs") {
      return promotedProofs
        .filter(
          (p) =>
            !q ||
            (p.id || "").toLowerCase().includes(q) ||
            (p.name || "").toLowerCase().includes(q) ||
            (p.claim_english || "").toLowerCase().includes(q),
        )
        .map(
          (p) =>
            ({
              kind: "control" as const,
              uses: `proof:${p.id}`,
              title: p.name || p.id,
              subtitle: "proof profile",
              accent: "proof",
            }) satisfies PaletteBlock,
        );
    }
    if (shelfTab === "controls") {
      return palette.filter((b) => b.kind === "control" && match(b));
    }
    return [];
  }, [palette, shelfTab, shelfQuery, promotedProofs]);

  const setShelf = (tab: ShelfCategory) => {
    setShelfTab(tab);
    setSheetBlock(null);
    void navigate({
      to: "/workshop",
      search: { id: searchId, shelf: tab },
      replace: true,
    });
  };

  const edges: PipelineEdge[] = doc.edges ?? [];
  const selectedStep = doc.steps.find((s) => s.id === selectedStepId) ?? null;

  const updateDoc = useCallback((next: PipelineDocument) => {
    setDoc(next);
    setDirty(true);
    setBoardErrors([]);
  }, []);

  const addBlock = useCallback(
    (block: PaletteBlock, at?: { x: number; y: number }) => {
      setDoc((prev) => {
        const step = stepFromBlock(block, prev.steps);
        if (at) step.layout = at;
        else {
          step.layout = {
            x: 80 + prev.steps.length * 40,
            y: 120 + (prev.steps.length % 3) * 30,
          };
        }
        // Freeform: do not auto-wire — operator draws ports
        return { ...prev, steps: [...prev.steps, step], edges: prev.edges ?? [] };
      });
      setDirty(true);
      setBoardErrors([]);
      setSelectedStepId((id) => id); // set after — use effect
      // Select new step on next tick via name in block
      setTimeout(() => {
        setDoc((prev) => {
          const last = prev.steps[prev.steps.length - 1];
          if (last) setSelectedStepId(last.id);
          return prev;
        });
      }, 0);
    },
    [],
  );

  const patchStep = (stepId: string, patch: Partial<PipelineStep>) => {
    setDoc((prev) => ({
      ...prev,
      steps: prev.steps.map((s) => (s.id === stepId ? { ...s, ...patch } : s)),
    }));
    setDirty(true);
    setBoardErrors([]);
  };

  const removeStep = (stepId: string) => {
    setDoc((prev) => ({
      ...prev,
      steps: prev.steps.filter((s) => s.id !== stepId),
      edges: (prev.edges ?? []).filter(
        (e) => e.from !== stepId && e.to !== stepId,
      ),
    }));
    setDirty(true);
    setBoardErrors([]);
    if (selectedStepId === stepId) setSelectedStepId(null);
  };

  const connect = (
    from: string,
    to: string,
    kind: string = "success",
    port?: string,
  ) => {
    if (from === to) return;
    setDoc((prev) => {
      const list = prev.edges ?? [];
      const key = edgeId(from, to, kind);
      if (list.some((e) => edgeId(e.from, e.to, e.kind || "success") === key)) {
        return prev;
      }
      // Cap success outs at 2 (professional multi-port default)
      if (kind !== "failure") {
        const successCount = list.filter(
          (e) => e.from === from && (e.kind || "success") !== "failure",
        ).length;
        if (successCount >= 2) {
          setError(
            "This block already has two success wires (max 2 outs). Remove a wire first.",
          );
          return prev;
        }
      }
      return {
        ...prev,
        edges: [...list, { from, to, kind, port: port || (kind === "failure" ? "fail" : "out") }],
      };
    });
    setDirty(true);
    setBoardErrors([]);
  };

  const removeEdge = (from: string, to: string, kind: string = "success") => {
    setDoc((prev) => ({
      ...prev,
      edges: (prev.edges ?? []).filter(
        (e) =>
          edgeId(e.from, e.to, e.kind || "success") !== edgeId(from, to, kind),
      ),
    }));
    setDirty(true);
    setBoardErrors([]);
    setSelectedEdgeKey(null);
  };

  const boardPoint = (clientX: number, clientY: number) => {
    const el = boardRef.current;
    if (!el) return { x: 0, y: 0 };
    const r = el.getBoundingClientRect();
    const p = panRef.current;
    return {
      x: clientX - r.left - p.x,
      y: clientY - r.top - p.y,
    };
  };

  const worldSize = useMemo(() => {
    let maxX = 1600;
    let maxY = 1000;
    doc.steps.forEach((s, i) => {
      const pos = ensureLayout(s, i);
      maxX = Math.max(maxX, pos.x + NODE_W + 480);
      maxY = Math.max(maxY, pos.y + NODE_H + 480);
    });
    return { w: maxX, h: maxY };
  }, [doc.steps]);

  const onNodeMouseDown = (e: ReactMouseEvent, stepId: string) => {
    if ((e.target as HTMLElement).dataset.port) return;
    e.preventDefault();
    e.stopPropagation();
    setSelectedStepId(stepId);
    setSelectedEdgeKey(null);
    const step = doc.steps.find((s) => s.id === stepId);
    const pos = ensureLayout(step!, doc.steps.indexOf(step!));
    const p = boardPoint(e.clientX, e.clientY);
    dragOffset.current = { x: p.x - pos.x, y: p.y - pos.y };
    setDraggingId(stepId);
  };

  useEffect(() => {
    if (!draggingId) return;
    const onMove = (e: MouseEvent) => {
      const p = boardPoint(e.clientX, e.clientY);
      const x = Math.max(8, p.x - dragOffset.current.x);
      const y = Math.max(8, p.y - dragOffset.current.y);
      setDoc((prev) => ({
        ...prev,
        steps: prev.steps.map((s) =>
          s.id === draggingId ? { ...s, layout: { x, y } } : s,
        ),
      }));
      setDirty(true);
    };
    const onUp = () => setDraggingId(null);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [draggingId]);

  useEffect(() => {
    if (!wiringFrom) return;
    const onMove = (e: MouseEvent) => {
      setWirePos(boardPoint(e.clientX, e.clientY));
    };
    const onUp = (e: MouseEvent) => {
      const target = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
      const toId = target?.dataset?.stepIn;
      if (toId && wiringFrom) {
        const kind = wiringPort === "fail" ? "failure" : "success";
        connect(wiringFrom, toId, kind, wiringPort);
      }
      setWiringFrom(null);
      setWiringPort("out");
      setWirePos(null);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [wiringFrom, wiringPort, doc.edges]);

  // Space for pan mode; middle-mouse / space+drag pans the board
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        spaceDown.current = true;
        e.preventDefault();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") spaceDown.current = false;
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  useEffect(() => {
    if (!panning) return;
    const onMove = (e: MouseEvent) => {
      setPan({
        x: panStart.current.panX + (e.clientX - panStart.current.x),
        y: panStart.current.panY + (e.clientY - panStart.current.y),
      });
    };
    const onUp = () => setPanning(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [panning]);

  useEffect(() => {
    if (!resizingInspector && !resizingShelf) return;
    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - resizeStart.current.x;
      if (resizeStart.current.kind === "inspector") {
        // Dragging left edge of inspector: moving left (dx negative) widens
        setInspectorW(
          Math.min(640, Math.max(220, resizeStart.current.w - dx)),
        );
      } else if (resizeStart.current.kind === "shelf") {
        setShelfW(Math.min(420, Math.max(180, resizeStart.current.w + dx)));
      }
    };
    const onUp = () => {
      setResizingInspector(false);
      setResizingShelf(false);
      resizeStart.current.kind = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [resizingInspector, resizingShelf]);

  const portCenter = (
    step: PipelineStep,
    index: number,
    side: "in" | "out" | "out2" | "fail",
  ) => {
    const pos = ensureLayout(step, index);
    if (side === "in") return { x: pos.x, y: pos.y + NODE_H / 2 };
    if (side === "fail") return { x: pos.x + NODE_W / 2, y: pos.y + NODE_H };
    if (side === "out2") return { x: pos.x + NODE_W, y: pos.y + NODE_H * 0.72 };
    return { x: pos.x + NODE_W, y: pos.y + NODE_H * 0.35 };
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      savePipeline({
        pipeline: {
          ...doc,
          edges: doc.edges ?? [],
          steps: doc.steps.map((s, i) => {
            const synced = syncAttachedPacks({
              ...s,
              enabled: s.enabled !== false,
              layout: ensureLayout(s, i),
            });
            return synced;
          }),
        },
        format: "yaml",
        overwrite: true,
      }),
    onSuccess: (data) => {
      setError(null);
      setDoc({
        ...data.pipeline,
        edges: data.pipeline.edges ?? [],
        steps: data.pipeline.steps.map((s, i) => ({
          ...s,
          layout: ensureLayout(s, i),
        })),
      });
      setDirty(false);
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      void navigate({
        to: "/workshop",
        search: { id: data.pipeline.id, shelf: shelfTab },
      });
      setRunBanner(`Saved ${data.pipeline.id}`);
    },
    onError: (err) => setError(formatApiError(err)),
  });

  // Keyboard: Delete removes selected block; Ctrl/Cmd+S saves
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable)
      ) {
        return;
      }
      if ((e.key === "Delete" || e.key === "Backspace") && selectedStepId) {
        e.preventDefault();
        const step = doc.steps.find((s) => s.id === selectedStepId);
        const hasWires = (doc.edges ?? []).some(
          (ed) => ed.from === selectedStepId || ed.to === selectedStepId,
        );
        if (
          hasWires &&
          !window.confirm(
            `Remove “${step?.name || selectedStepId}” and its wires from the board?`,
          )
        ) {
          return;
        }
        removeStep(selectedStepId);
        setRunBanner("Block removed from board");
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveMutation.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const tryRun = () => {
    const errs = validateCompositionForRun(doc);
    setBoardErrors(errs);
    if (errs.length) {
      setError(errs[0]);
      setRunBanner(null);
      return;
    }
    setError(null);
    runMutation.mutate();
  };

  const runMutation = useMutation({
    mutationFn: async () => {
      const saved = await saveMutation.mutateAsync();
      setLive(
        Object.fromEntries(
          saved.pipeline.steps.map((s) => [
            s.id,
            s.enabled === false ? "skipped" : "idle",
          ]),
        ),
      );
      setMini({});
      const prefs = loadModelsPrefs();
      setRunBanner(
        `Saved · running (${modeLabel(prefs.mode)}) along your wires…`,
      );
      const proofProfile =
        (saved.pipeline.defaults as { proof_profile?: string } | undefined)
          ?.proof_profile || undefined;
      return runCompositionPipeline({
        pipeline_id: saved.pipeline.id,
        input_text: inputText,
        async: true,
        llm: llmPayloadFromPrefs(prefs),
        proof_profile: proofProfile,
        attest:
          Boolean(
            (saved.pipeline.defaults as { attest?: boolean } | undefined)
              ?.attest,
          ) || undefined,
      });
    },
    onSuccess: async (result) => {
      setError(null);
      setBoardErrors([]);
      if (result.mode === "queued") {
        const jobId = String(result.job_id ?? result.id ?? "");
        if (!jobId) return;
        setLastJobId(jobId);
        notifyPipelineQueued(queryClient, jobId, { pipeline_id: doc.id });
        for (let i = 0; i < 80; i++) {
          await new Promise((r) => setTimeout(r, 600));
          try {
            const job = await getJob(jobId);
            const fullResult = job.result as
              | {
                  final_status?: string;
                  error?: string;
                  run_trace?: { steps?: RunTraceStep[] };
                }
              | undefined;
            const trace = fullResult?.run_trace;
            if (trace?.steps) {
              const map: LiveStatus = {};
              const miniMap: StepMini = {};
              for (const s of trace.steps) {
                map[s.step_id] = s.status;
                const sum = s.summary || {};
                if (s.error) miniMap[s.step_id] = s.error.slice(0, 80);
                else if (typeof sum.total_redactions === "number") {
                  miniMap[s.step_id] = `${sum.total_redactions} redactions`;
                } else if (typeof sum.governance_decision === "string") {
                  miniMap[s.step_id] = String(sum.governance_decision);
                } else if (sum.approved) miniMap[s.step_id] = "approved";
                else if (typeof sum.attestation_id === "string") {
                  miniMap[s.step_id] = "attested";
                } else if (typeof sum.handoff_pipeline_id === "string") {
                  miniMap[s.step_id] = `→ ${sum.handoff_pipeline_id}`;
                } else if (typeof sum.child_final_status === "string") {
                  miniMap[s.step_id] = `child ${sum.child_final_status}`;
                } else if (s.status === "skipped" && sum.reason) {
                  miniMap[s.step_id] = String(sum.reason).slice(0, 40);
                }
              }
              if (job.status === "running" || job.status === "queued") {
                for (const step of doc.steps) {
                  if (!map[step.id] && step.enabled !== false) {
                    map[step.id] = "running";
                    break;
                  }
                }
              }
              setLive(map);
              setMini(miniMap);
            }
            const status = String(job.status ?? "");
            if (
              status === "completed" ||
              status === "failed" ||
              status === "awaiting_approval"
            ) {
              const fs = fullResult?.final_status;
              if (status === "awaiting_approval") {
                setRunBanner("Paused for approval — open last job to approve");
              } else if (fs === "failed") {
                setRunBanner(
                  fullResult?.error
                    ? `Failed: ${fullResult.error}`
                    : "Composition failed — open last job for the full trace",
                );
              } else {
                setRunBanner("Run finished — cards show step results");
              }
              break;
            }
          } catch {
            /* poll */
          }
        }
      }
    },
    onError: (err) => {
      setError(formatApiError(err));
      setRunBanner(null);
    },
  });

  const installTemplate = useMutation({
    mutationFn: async (templateId: string) => {
      const detail = await getPipelineTemplate(templateId);
      if (!detail.pipeline) throw new Error("Template has no pipeline document");
      // Seed linear edges if missing so freeform board has wires
      const p = detail.pipeline;
      let edges = p.edges ?? [];
      if (!edges.length && p.steps.length > 1) {
        edges = p.steps.slice(0, -1).map((s, i) => ({
          from: s.id,
          to: p.steps[i + 1].id,
          kind: "success",
        }));
      }
      return savePipeline({
        pipeline: {
          ...p,
          edges,
          steps: p.steps.map((s, i) => ({
            ...s,
            layout: ensureLayout(s, i),
            enabled: s.enabled !== false,
          })),
        },
        format: "yaml",
        overwrite: true,
      });
    },
    onSuccess: (data) => {
      setDoc({
        ...data.pipeline,
        edges: data.pipeline.edges ?? [],
        steps: data.pipeline.steps.map((s, i) => ({
          ...s,
          layout: ensureLayout(s, i),
        })),
      });
      setDirty(false);
      setSelectedStepId(data.pipeline.steps[0]?.id ?? null);
      void queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      void navigate({
        to: "/workshop",
        search: { id: data.pipeline.id, shelf: "library" },
      });
      setRunBanner(`Loaded ${data.pipeline.id} — drag nodes and rewire freely`);
    },
    onError: (err) => setError(formatApiError(err)),
  });

  return (
    <div
      className={[
        "flex h-full min-h-0 w-full flex-col overflow-hidden bg-[#0c0f14]",
        resizingInspector || resizingShelf ? "select-none" : "",
      ].join(" ")}
    >
      <header className="relative z-20 shrink-0 border-b border-white/10 bg-[#12161e]">
        {/* Row 1 — navigation + open board + primary actions */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 py-2">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            <Layers className="h-4 w-4 shrink-0 text-cyan-400" aria-hidden />
            <span className="text-sm font-semibold tracking-tight text-cyan-100">
              Workbench
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2.5 text-xs"
              asChild
            >
              <Link to="/studio" search={{ tab: undefined }}>
                Studio
              </Link>
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2.5 text-xs"
              asChild
            >
              <Link to="/workshop/library">Library</Link>
            </Button>
          </div>

          <div className="flex min-w-0 flex-1 flex-wrap items-end gap-2 sm:min-w-[14rem]">
            <label className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                Open board
              </span>
              <select
                className="h-8 w-full min-w-0 rounded-md border border-white/10 bg-black/40 px-2 text-xs text-zinc-100"
                value={searchId ?? ""}
                title={
                  searchId
                    ? `Open saved pipeline: ${searchId}`
                    : "Choose a saved pipeline or start a new board"
                }
                aria-label="Open saved pipeline board"
                onChange={(e) => {
                  const id = e.target.value || undefined;
                  if (dirty) {
                    const ok = window.confirm(
                      "Switch board? Unsaved changes will be discarded.",
                    );
                    if (!ok) return;
                  }
                  setRestoredFromSession(null);
                  void navigate({
                    to: "/workshop",
                    search: { id, shelf: shelfTab },
                  });
                  if (!id) {
                    const blank = emptyPipeline();
                    blank.steps = blank.steps.map((s, i) => ({
                      ...s,
                      layout: ensureLayout(s, i),
                    }));
                    setDoc({ ...blank, edges: [] });
                    setSelectedStepId(blank.steps[0]?.id ?? null);
                    setDirty(false);
                    rememberLastPipelineId(null);
                  }
                }}
              >
                <option value="">New board…</option>
                {(pipelinesQuery.data?.pipelines ?? []).map((p) => (
                  <option key={p.id} value={p.id} title={`${p.name || p.id} (${p.id})`}>
                    {p.name && p.name !== p.id
                      ? `${p.name} — ${p.id}`
                      : p.id}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {dirty ? (
              <span
                className="rounded-full bg-amber-500/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200"
                title="This board has unsaved changes"
              >
                Unsaved
              </span>
            ) : null}
            <Button
              size="sm"
              variant="secondary"
              className="h-8 px-3 text-xs"
              disabled={saveMutation.isPending || runMutation.isPending}
              onClick={() => saveMutation.mutate()}
              title="Save pipeline to disk (Ctrl/Cmd+S)"
            >
              <Save className="mr-1.5 h-3.5 w-3.5" />
              {dirty ? "Save*" : "Save"}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="h-8 px-3 text-xs"
              title="Download a JSON snapshot of this board"
              onClick={() => {
                const exportDoc = {
                  ...doc,
                  steps: doc.steps.map((s) => syncAttachedPacks(s)),
                  edges: doc.edges ?? [],
                };
                downloadText(
                  `${doc.id || "pipeline"}.json`,
                  JSON.stringify(exportDoc, null, 2),
                  "application/json",
                );
                setRunBanner(
                  "Exported board snapshot (JSON). Use Save to keep it on this instance.",
                );
              }}
            >
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Export
            </Button>
            <Button
              size="sm"
              className="h-8 px-3.5 text-xs font-semibold"
              disabled={
                runMutation.isPending ||
                saveMutation.isPending ||
                doc.steps.length === 0
              }
              title={
                doc.steps.length === 0
                  ? "Add at least one block from the shelf, then Run"
                  : saveMutation.isPending
                    ? "Saving before run…"
                    : "Validate, save if needed, and queue this pipeline"
              }
              onClick={() => tryRun()}
            >
              <Play className="mr-1.5 h-3.5 w-3.5" />
              {runMutation.isPending ? "Running…" : "Run"}
            </Button>
            {lastJobId ? (
              <Button
                size="sm"
                variant="secondary"
                className="h-8 px-3 text-xs"
                asChild
              >
                <Link to="/jobs" search={{ id: lastJobId }} title={lastJobId}>
                  Last run
                </Link>
              </Button>
            ) : null}
          </div>
        </div>

        {/* Row 2 — identity fields (full width, labeled, no cut-off) */}
        <div className="grid grid-cols-1 gap-2 border-t border-white/5 px-3 py-2 sm:grid-cols-2 lg:grid-cols-12 lg:items-end">
          <label className="flex min-w-0 flex-col gap-0.5 lg:col-span-4">
            <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              Pipeline id
            </span>
            <Input
              className="h-8 border-white/10 bg-black/30 font-mono text-xs text-zinc-100"
              value={doc.id}
              title={doc.id}
              aria-label="Pipeline id"
              onChange={(e) =>
                updateDoc({ ...doc, id: e.target.value.trim() })
              }
            />
          </label>
          <label className="flex min-w-0 flex-col gap-0.5 lg:col-span-4">
            <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              Display name
            </span>
            <Input
              className="h-8 border-white/10 bg-black/30 text-xs text-zinc-100"
              value={doc.name}
              title={doc.name}
              aria-label="Pipeline display name"
              onChange={(e) => updateDoc({ ...doc, name: e.target.value })}
            />
          </label>
          <div className="flex min-w-0 flex-col gap-0.5 lg:col-span-4">
            <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
              Proof profile
            </span>
            {(() => {
              const boundProof = (
                doc.defaults as { proof_profile?: string } | undefined
              )?.proof_profile;
              if (!boundProof) {
                return (
                  <p
                    className="flex h-8 items-center rounded-md border border-dashed border-white/10 px-2 text-[11px] text-zinc-500"
                    title="Open the Proofs shelf and click a promoted profile to bind it for Run"
                  >
                    None — bind from Proofs shelf
                  </p>
                );
              }
              return (
                <div className="flex h-8 min-w-0 items-center gap-1.5">
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate rounded-md border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-1.5 text-left font-mono text-[11px] text-emerald-100 hover:bg-emerald-500/25"
                    title={`${boundProof} — click to clear binding`}
                    onClick={() => {
                      const nextDefaults = {
                        ...(doc.defaults || {}),
                      } as Record<string, unknown>;
                      delete nextDefaults.proof_profile;
                      updateDoc({
                        ...doc,
                        defaults: nextDefaults as typeof doc.defaults,
                      });
                      setDirty(true);
                      setRunBanner("Cleared proof profile binding.");
                    }}
                  >
                    {boundProof}
                  </button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-8 shrink-0 px-2 text-[11px] text-zinc-400"
                    title={`Clear proof profile ${boundProof}`}
                    onClick={() => {
                      const nextDefaults = {
                        ...(doc.defaults || {}),
                      } as Record<string, unknown>;
                      delete nextDefaults.proof_profile;
                      updateDoc({
                        ...doc,
                        defaults: nextDefaults as typeof doc.defaults,
                      });
                      setDirty(true);
                      setRunBanner("Cleared proof profile binding.");
                    }}
                  >
                    Clear
                  </Button>
                </div>
              );
            })()}
          </div>
        </div>

        {/* Row 3 — how to use (always visible, full text) */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-white/5 bg-black/20 px-3 py-1.5 text-[11px] leading-snug text-zinc-500">
          <span title="Pan the board: hold Space and drag, middle-mouse drag, or trackpad">
            <strong className="font-medium text-zinc-400">Pan:</strong> Space+drag
          </span>
          <span className="hidden text-zinc-700 sm:inline" aria-hidden>
            ·
          </span>
          <span title="Drag agents, packs, and controls from the left shelf onto the board">
            <strong className="font-medium text-zinc-400">Build:</strong> drag from
            shelf
          </span>
          <span className="hidden text-zinc-700 sm:inline" aria-hidden>
            ·
          </span>
          <span title="Without wires, steps run top-to-bottom in document order">
            <strong className="font-medium text-zinc-400">Order:</strong>{" "}
            {(doc.edges?.length ?? 0) === 0 && doc.steps.length > 1
              ? "document (linear) — wires optional"
              : doc.edges && doc.edges.length > 0
                ? `${doc.edges.length} wire${doc.edges.length === 1 ? "" : "s"}`
                : "add blocks, then Run"}
          </span>
          <span className="hidden text-zinc-700 md:inline" aria-hidden>
            ·
          </span>
          <span className="hidden md:inline" title="Author agents, packs, and proofs in Studio; assemble here">
            <strong className="font-medium text-zinc-400">Flow:</strong> Studio →
            shelf → Run → Runs
          </span>
        </div>
      </header>

      {restoredFromSession && searchId === restoredFromSession ? (
        <div className="relative z-10 flex shrink-0 flex-wrap items-center gap-3 border-b border-cyan-500/25 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-50/95">
          <p className="min-w-0 flex-1 leading-relaxed">
            <strong className="font-semibold text-cyan-100">
              Opened your last board.
            </strong>{" "}
            <span className="break-all font-mono text-[11px] text-cyan-200/90">
              {restoredFromSession}
            </span>
            <span className="mt-0.5 block text-[11px] text-cyan-100/70 sm:mt-0 sm:ml-1 sm:inline">
              Keep editing, open another board from the menu above, or start
              new.
            </span>
          </p>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              className="h-8 px-3 text-xs"
              onClick={() => {
                setRestoredFromSession(null);
                if (dirty) {
                  const ok = window.confirm(
                    "Start a new board? Unsaved changes will be discarded.",
                  );
                  if (!ok) return;
                }
                rememberLastPipelineId(null);
                void navigate({
                  to: "/workshop",
                  search: { id: undefined, shelf: shelfTab },
                });
                const blank = emptyPipeline();
                blank.steps = blank.steps.map((s, i) => ({
                  ...s,
                  layout: ensureLayout(s, i),
                }));
                setDoc({ ...blank, edges: [] });
                setSelectedStepId(blank.steps[0]?.id ?? null);
                setDirty(false);
                setRunBanner(null);
              }}
            >
              New board
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-8 px-3 text-xs text-zinc-300"
              onClick={() => setRestoredFromSession(null)}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}

      {(error || runBanner || boardErrors.length > 0) && (
        <div className="relative z-10 shrink-0 space-y-2 border-b border-white/10 px-4 py-2">
          {boardErrors.length > 0 ? (
            <Alert variant="destructive">
              <AlertDescription>
                <p className="mb-1 font-medium">Fix before run</p>
                <ul className="list-disc space-y-0.5 pl-4 text-sm">
                  {boardErrors.map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : error ? (
            <Alert variant="destructive">
              <AlertDescription className="flex flex-wrap items-start justify-between gap-2">
                <span className="min-w-0 flex-1">{error}</span>
                <button
                  type="button"
                  className="shrink-0 text-xs text-zinc-400 underline-offset-2 hover:underline"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </button>
              </AlertDescription>
            </Alert>
          ) : (
            <div className="flex flex-wrap items-center gap-3 text-sm text-sky-300">
              <Sparkles className="h-4 w-4 shrink-0 animate-pulse" />
              <span className="min-w-0 flex-1 break-words">{runBanner}</span>
              {lastJobId ? (
                <Link
                  to="/jobs"
                  search={{ id: lastJobId }}
                  className="shrink-0 text-cyan-200 underline-offset-2 hover:underline"
                >
                  Open last job
                </Link>
              ) : null}
              <button
                type="button"
                className="shrink-0 text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
                onClick={() => setRunBanner(null)}
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      )}

      <div className="relative flex min-h-0 flex-1">
        {/* Shelf — building blocks catalog */}
        <aside
          className="relative flex shrink-0 flex-col border-r border-white/10 bg-[#10141c]"
          style={{ width: shelfW }}
        >
          <div className="border-b border-white/10 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
              Shelf
            </p>
            <p className="text-[11px] leading-snug text-zinc-500">
              Building blocks. Click a row to inspect, or drag onto the board.
              Proofs bind to this pipeline (they are not steps).
            </p>
          </div>
          {/* Resize handle — shelf */}
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize shelf"
            title="Drag to resize shelf"
            className="absolute inset-y-0 right-0 z-20 w-1.5 cursor-col-resize hover:bg-cyan-400/40 active:bg-cyan-400/60"
            onMouseDown={(e) => {
              e.preventDefault();
              resizeStart.current = {
                x: e.clientX,
                w: shelfW,
                kind: "shelf",
              };
              setResizingShelf(true);
            }}
          />
          <div className="flex flex-wrap gap-0.5 border-b border-white/10 p-1.5">
            {(
              [
                ["agents", "Agents"],
                ["packs", "Packs"],
                ["proofs", "Proofs"],
                ["controls", "Controls"],
                ["library", "Library"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setShelf(id)}
                className={`rounded px-1.5 py-1 text-[10px] font-medium ${
                  shelfTab === id
                    ? "bg-cyan-500/20 text-cyan-100"
                    : "text-zinc-500 hover:bg-white/5 hover:text-zinc-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {shelfTab !== "library" ? (
            <>
              <div className="border-b border-white/10 px-2 py-1.5">
                <Input
                  className="h-8 border-white/10 bg-black/30 text-xs"
                  placeholder="Search shelf…"
                  value={shelfQuery}
                  onChange={(e) => setShelfQuery(e.target.value)}
                  aria-label="Search building blocks"
                />
              </div>
              <div className="flex-1 space-y-1 overflow-y-auto p-2">
                {shelfItems.length === 0 ? (
                  <div className="space-y-2 px-1 py-4 text-center">
                    <p className="text-[11px] text-zinc-500">
                      {shelfTab === "proofs" && !shelfQuery.trim()
                        ? "No promoted proof profiles yet."
                        : shelfQuery.trim()
                          ? "No blocks match. Try another category or clear search."
                          : "No blocks match. Try another category."}
                    </p>
                    {shelfTab === "proofs" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        className="text-xs"
                        asChild
                      >
                        <Link to="/studio" search={{ tab: "proofs" }}>
                          Author in Studio · Proofs
                        </Link>
                      </Button>
                    ) : null}
                  </div>
                ) : (
                  shelfItems.map((block) => {
                    const Icon = blockIcon(block.kind);
                    const mat = maturityForUses(block.uses);
                    return (
                      <div
                        key={block.uses}
                        draggable
                        onDragStart={(e) => {
                          if (block.uses.startsWith("proof:")) {
                            e.preventDefault();
                            return;
                          }
                          e.dataTransfer.setData(
                            "application/apxv-block",
                            block.uses,
                          );
                        }}
                        className={`flex cursor-grab items-start gap-2 rounded-lg border border-white/10 p-2 active:cursor-grabbing ${kindTint(block.kind)}`}
                      >
                        <button
                          type="button"
                          className="min-w-0 flex-1 text-left"
                          onClick={() => {
                            if (block.uses.startsWith("proof:")) {
                              const pid = block.uses.slice("proof:".length);
                              setDoc((d) => ({
                                ...d,
                                defaults: {
                                  ...(d.defaults || {}),
                                  proof_profile: pid,
                                },
                              }));
                              setDirty(true);
                              setRunBanner(
                                `Bound proof profile ${pid} on this pipeline (Save + Run).`,
                              );
                              return;
                            }
                            setSheetBlock(block);
                          }}
                          title={
                            block.uses.startsWith("proof:")
                              ? "Bind this proof profile to the pipeline"
                              : "Open ingredient sheet"
                          }
                        >
                          <div className="mb-0.5 flex items-center gap-1">
                            <Icon className="h-3 w-3 shrink-0 text-zinc-300" />
                            <span
                              className={`rounded px-1 text-[8px] font-semibold uppercase ${maturityBadgeClass(mat)}`}
                            >
                              {mat}
                            </span>
                          </div>
                          <p className="truncate text-[11px] font-medium text-zinc-100">
                            {block.title}
                          </p>
                          <p className="truncate text-[9px] text-zinc-500">
                            {kindLabel(block.kind)} · {block.subtitle}
                          </p>
                        </button>
                        {block.uses.startsWith("proof:") ? (
                          <button
                            type="button"
                            className="rounded p-0.5 text-emerald-400/80 hover:bg-emerald-500/15 hover:text-emerald-200"
                            title="Bind proof profile to this pipeline"
                            onClick={() => {
                              const pid = block.uses.slice("proof:".length);
                              setDoc((d) => ({
                                ...d,
                                defaults: {
                                  ...(d.defaults || {}),
                                  proof_profile: pid,
                                },
                              }));
                              setDirty(true);
                              setRunBanner(
                                `Bound proof profile ${pid} on this pipeline (Save + Run).`,
                              );
                            }}
                          >
                            <Plus className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="rounded p-0.5 text-zinc-400 hover:bg-white/10 hover:text-white"
                            title="Add to board"
                            onClick={() => {
                              addBlock(block);
                              setSheetBlock(null);
                            }}
                          >
                            <Plus className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 space-y-2 overflow-y-auto p-2">
              <p className="px-1 text-[9px] font-bold uppercase text-zinc-500">
                Example pipelines
              </p>
              {(templatesQuery.data?.templates ?? []).map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className="mb-0.5 w-full rounded-lg border border-white/10 bg-black/20 px-2 py-2 text-left hover:bg-white/5"
                  onClick={() => installTemplate.mutate(t.id)}
                >
                  <span
                    className={`mb-1 inline-block rounded px-1 text-[8px] font-semibold uppercase ${maturityBadgeClass("Example")}`}
                  >
                    Example
                  </span>
                  <p className="text-[11px] font-medium text-zinc-100">
                    {t.name || t.id}
                  </p>
                  <p className="truncate font-mono text-[9px] text-zinc-500">
                    {t.id}
                  </p>
                </button>
              ))}
              <p className="mt-3 px-1 text-[9px] font-bold uppercase text-zinc-500">
                Saved locally
              </p>
              {(pipelinesQuery.data?.pipelines ?? []).length === 0 ? (
                <p className="px-1 text-[11px] text-zinc-500">
                  No saved pipelines yet. Save from the board toolbar.
                </p>
              ) : (
                (pipelinesQuery.data?.pipelines ?? []).map((p) => (
                  <div
                    key={p.id}
                    className="mb-1 rounded-lg border border-white/10 px-2 py-2"
                  >
                    <p className="text-[11px] font-medium text-zinc-100">
                      {p.name || p.id}
                    </p>
                    <p className="truncate font-mono text-[9px] text-zinc-500">
                      {p.id}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      <button
                        type="button"
                        className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-zinc-300 hover:bg-white/10"
                        onClick={() => {
                          if (dirty) {
                            const ok = window.confirm(
                              "Switch pipeline? Unsaved board changes will be discarded.",
                            );
                            if (!ok) return;
                          }
                          void navigate({
                            to: "/workshop",
                            search: { id: p.id, shelf: "library" },
                          });
                        }}
                      >
                        Open
                      </button>
                      {p.id !== doc.id ? (
                        <button
                          type="button"
                          className="rounded bg-cyan-500/15 px-1.5 py-0.5 text-[9px] text-cyan-200 hover:bg-cyan-500/25"
                          title="Place as pipeline link block on this board"
                          onClick={() => {
                            const block = pipelineRefBlock(
                              p.id,
                              p.name || p.id,
                            );
                            setDoc((prev) => {
                              const step = stepFromBlock(block, prev.steps);
                              step.name = `→ ${p.name || p.id}`;
                              step.config = {
                                pipeline_id: p.id,
                                run_child: true,
                              };
                              step.layout = {
                                x: 100 + prev.steps.length * 24,
                                y: 160 + (prev.steps.length % 3) * 28,
                              };
                              return {
                                ...prev,
                                steps: [...prev.steps, step],
                                edges: prev.edges ?? [],
                              };
                            });
                            setDirty(true);
                            setBoardErrors([]);
                            setRunBanner(
                              `Pipeline block “${p.id}” placed — wire it into the flow`,
                            );
                          }}
                        >
                          Place on board
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
              <div className="border-t border-white/10 pt-2">
                <Button
                  size="sm"
                  variant="secondary"
                  className="w-full text-xs"
                  asChild
                >
                  <Link to="/studio" search={{ tab: "packs" }}>
                    Open Studio · Packs
                  </Link>
                </Button>
              </div>
            </div>
          )}
        </aside>

        {/* Freeform board — fixed viewport; pan the world inside */}
        <main
          ref={boardRef}
          className={[
            "relative min-h-0 min-w-0 flex-1 overflow-hidden",
            panning || spaceDown.current ? "cursor-grabbing" : "cursor-default",
          ].join(" ")}
          style={{
            backgroundColor: "#0a0d12",
            backgroundImage:
              "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)",
            backgroundSize: "20px 20px",
            backgroundPosition: `${pan.x}px ${pan.y}px`,
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const uses = e.dataTransfer.getData("application/apxv-block");
            const block = palette.find((b) => b.uses === uses);
            if (!block) return;
            const p = boardPoint(e.clientX, e.clientY);
            addBlock(block, { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 });
          }}
          onWheel={(e) => {
            // Trackpad / mouse wheel pans the board (not the page)
            e.preventDefault();
            setPan((p) => ({
              x: p.x - e.deltaX,
              y: p.y - e.deltaY,
            }));
          }}
          onMouseDown={(e) => {
            const target = e.target as HTMLElement;
            const onNode =
              target.closest("[data-board-node]") ||
              target.dataset.port ||
              target.dataset.stepIn;
            const onWire = target.closest("path");
            const middle = e.button === 1;
            const spacePan = spaceDown.current && e.button === 0;
            // Empty canvas drag pans (nodes still grab to move)
            const emptyPan =
              e.button === 0 && !onNode && !onWire && !wiringFrom;
            if (middle || spacePan || emptyPan) {
              e.preventDefault();
              setSelectedEdgeKey(null);
              if (!onNode) setSelectedStepId(null);
              panStart.current = {
                x: e.clientX,
                y: e.clientY,
                panX: pan.x,
                panY: pan.y,
              };
              setPanning(true);
              return;
            }
          }}
          onClick={(e) => {
            if (panning) return;
            const target = e.target as HTMLElement;
            if (!target.closest("[data-board-node]")) {
              setSelectedEdgeKey(null);
            }
          }}
        >
          <div
            className="absolute left-0 top-0 origin-top-left will-change-transform"
            style={{
              width: worldSize.w,
              height: worldSize.h,
              transform: `translate(${pan.x}px, ${pan.y}px)`,
            }}
          >
            {/* Wires */}
            <svg
              className="pointer-events-none absolute left-0 top-0 overflow-visible"
              width={worldSize.w}
              height={worldSize.h}
            >
              {edges.map((edge) => {
                const fromStep = doc.steps.find((s) => s.id === edge.from);
                const toStep = doc.steps.find((s) => s.id === edge.to);
                if (!fromStep || !toStep) return null;
                const fi = doc.steps.indexOf(fromStep);
                const ti = doc.steps.indexOf(toStep);
                const fromPort =
                  edge.kind === "failure"
                    ? "fail"
                    : edge.port === "out2"
                      ? "out2"
                      : "out";
                const a = portCenter(fromStep, fi, fromPort);
                const b = portCenter(toStep, ti, "in");
                const midX = (a.x + b.x) / 2;
                const path = `M ${a.x} ${a.y} C ${midX} ${a.y}, ${midX} ${b.y}, ${b.x} ${b.y}`;
                const key = edgeId(edge.from, edge.to, edge.kind || "success");
                const lit =
                  live[edge.from] === "succeeded" ||
                  live[edge.to] === "running" ||
                  live[edge.to] === "succeeded";
                const selected = selectedEdgeKey === key;
                const stroke =
                  edge.kind === "failure"
                    ? lit
                      ? "#f87171"
                      : "#7f1d1d"
                    : lit
                      ? "#38bdf8"
                      : selected
                        ? "#a5f3fc"
                        : "#3f3f46";
                return (
                  <g key={key} className="pointer-events-auto">
                    <path
                      d={path}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={14}
                      className="cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEdgeKey(key);
                        setSelectedStepId(null);
                      }}
                    />
                    <path
                      d={path}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={selected ? 3 : 2}
                      strokeDasharray={edge.kind === "failure" ? "6 4" : undefined}
                      markerEnd="url(#apxv-arrow)"
                    />
                  </g>
                );
              })}
              {wiringFrom && wirePos && (() => {
                const fromStep = doc.steps.find((s) => s.id === wiringFrom);
                if (!fromStep) return null;
                const side =
                  wiringPort === "fail"
                    ? "fail"
                    : wiringPort === "out2"
                      ? "out2"
                      : "out";
                const a = portCenter(
                  fromStep,
                  doc.steps.indexOf(fromStep),
                  side,
                );
                const midX = (a.x + wirePos.x) / 2;
                return (
                  <path
                    d={`M ${a.x} ${a.y} C ${midX} ${a.y}, ${midX} ${wirePos.y}, ${wirePos.x} ${wirePos.y}`}
                    fill="none"
                    stroke={wiringPort === "fail" ? "#f87171" : "#67e8f9"}
                    strokeWidth={2}
                    strokeDasharray="4 3"
                  />
                );
              })()}
              <defs>
                <marker
                  id="apxv-arrow"
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L6,3 L0,6 Z" fill="#64748b" />
                </marker>
              </defs>
            </svg>

            {doc.steps.length === 0 && (
              <div className="absolute left-1/2 top-1/3 z-10 w-80 -translate-x-1/2 rounded-2xl border border-dashed border-white/15 bg-black/50 p-8 text-center backdrop-blur">
                <p className="font-semibold text-zinc-100">Empty Workbench</p>
                <p className="mt-2 text-sm text-zinc-500">
                  Drop agents and packs from the shelf, open the pipeline
                  library, or author new building blocks in Studio. Pan with
                  Space+drag, middle-mouse, or trackpad. Multi-step boards run
                  in document order unless you draw wires.
                </p>
                <div className="mt-4 flex flex-col gap-2">
                  <Button size="sm" className="w-full" asChild>
                    <Link to="/workshop/library">Open pipeline library</Link>
                  </Button>
                  <Button size="sm" variant="secondary" className="w-full" asChild>
                    <Link to="/studio" search={{ tab: "agents" }}>
                      Author in Studio
                    </Link>
                  </Button>
                </div>
              </div>
            )}

            {/* Hover truth card */}
            {hoverTip &&
              (() => {
                const step = doc.steps.find((s) => s.id === hoverTip.stepId);
                if (!step) return null;
                const kind = usesKind(step.uses);
                const mat = maturityForUses(step.uses);
                const purpose = purposeForBlock({
                  title: step.name,
                  subtitle: step.uses,
                  uses: step.uses,
                  kind,
                });
                return (
                  <div
                    className="pointer-events-none absolute z-30 w-52 rounded-lg border border-cyan-500/30 bg-[#0c1018]/95 p-2.5 shadow-xl backdrop-blur"
                    style={{ left: hoverTip.x, top: hoverTip.y }}
                  >
                    <div className="mb-1 flex items-center gap-1.5">
                      <span className="rounded bg-white/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-zinc-200">
                        {kindLabel(kind)}
                      </span>
                      <span
                        className={`rounded px-1 py-0.5 text-[8px] font-semibold uppercase ${maturityBadgeClass(mat)}`}
                      >
                        {mat}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-zinc-50">
                      {step.name}
                    </p>
                    <p className="mt-1 text-[10px] leading-snug text-zinc-400">
                      {purpose}
                    </p>
                    <p className="mt-1 truncate font-mono text-[9px] text-zinc-500">
                      {step.uses}
                    </p>
                    {live[step.id] && live[step.id] !== "idle" ? (
                      <p className="mt-1 text-[9px] text-sky-300">
                        Status: {live[step.id]}
                        {mini[step.id] ? ` · ${mini[step.id]}` : ""}
                      </p>
                    ) : null}
                    {step.enabled === false ? (
                      <p className="mt-1 text-[9px] text-zinc-500">Disabled</p>
                    ) : null}
                  </div>
                );
              })()}

            {/* Nodes */}
            {doc.steps.map((step, index) => {
              const pos = ensureLayout(step, index);
              const kind = usesKind(step.uses);
              const Icon = blockIcon(kind);
              const st = live[step.id] ?? "idle";
              const off = step.enabled === false;
              return (
                <div
                  key={step.id}
                  data-board-node={step.id}
                  className={`absolute select-none rounded-xl border-2 bg-[#151a24] shadow-xl ${statusRing(st, off)} ${
                    selectedStepId === step.id ? "ring-2 ring-cyan-400/80" : ""
                  }`}
                  style={{
                    left: pos.x,
                    top: pos.y,
                    width: NODE_W,
                    height: NODE_H,
                    cursor: draggingId === step.id ? "grabbing" : "grab",
                  }}
                  onMouseDown={(e) => onNodeMouseDown(e, step.id)}
                  onMouseEnter={() => {
                    if (draggingId || wiringFrom) return;
                    setHoverTip({
                      stepId: step.id,
                      x: pos.x + NODE_W + 8,
                      y: pos.y,
                    });
                  }}
                  onMouseLeave={() => setHoverTip(null)}
                >
                  {/* input port */}
                  <button
                    type="button"
                    data-port="in"
                    data-step-in={step.id}
                    className="absolute -left-2 top-1/2 z-10 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-cyan-300 bg-[#0c0f14] hover:scale-125 hover:bg-cyan-400"
                    title="Input port — drop a wire here"
                    onMouseUp={(e) => {
                      e.stopPropagation();
                      if (wiringFrom) {
                        const kind =
                          wiringPort === "fail" ? "failure" : "success";
                        connect(wiringFrom, step.id, kind, wiringPort);
                        setWiringFrom(null);
                        setWiringPort("out");
                        setWirePos(null);
                      }
                    }}
                  />
                  {/* success out (primary) */}
                  <button
                    type="button"
                    data-port="out"
                    className="absolute -right-2 top-[32%] z-10 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 border-sky-400 bg-[#0c0f14] hover:scale-125 hover:bg-sky-400"
                    title="Success out 1 — drag to an input"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setWiringFrom(step.id);
                      setWiringPort("out");
                      setWirePos(boardPoint(e.clientX, e.clientY));
                    }}
                  />
                  {/* success out 2 (fan-out) */}
                  <button
                    type="button"
                    data-port="out2"
                    className="absolute -right-2 top-[68%] z-10 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 border-cyan-600 bg-[#0c0f14] hover:scale-125 hover:bg-cyan-400"
                    title="Success out 2 — fan-out to another stage"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setWiringFrom(step.id);
                      setWiringPort("out2");
                      setWirePos(boardPoint(e.clientX, e.clientY));
                    }}
                  />
                  {/* failure out */}
                  <button
                    type="button"
                    data-port="fail"
                    className="absolute bottom-0 left-1/2 z-10 h-3 w-3 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-red-400/80 bg-[#0c0f14] hover:scale-125 hover:bg-red-400"
                    title="Failure out — optional branch"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setWiringFrom(step.id);
                      setWiringPort("fail");
                      setWirePos(boardPoint(e.clientX, e.clientY));
                    }}
                  />
                  <div className="flex h-full flex-col p-2.5">
                    <div className="mb-1 flex items-center justify-between">
                      <Icon className="h-3.5 w-3.5 text-zinc-300" />
                      <span className="text-[8px] uppercase tracking-wide text-zinc-500">
                        {off
                          ? "off"
                          : st === "idle"
                            ? kind
                            : st}
                        {step.attached_packs && step.attached_packs.length
                          ? ` · +${step.attached_packs.length}p`
                          : ""}
                      </span>
                    </div>
                    <p className="line-clamp-2 text-xs font-semibold leading-snug text-zinc-50">
                      {step.name}
                    </p>
                    <p className="mt-auto truncate font-mono text-[8px] text-zinc-500">
                      {step.uses}
                    </p>
                    {mini[step.id] ? (
                      <p
                        className={`mt-1 line-clamp-2 text-[9px] ${
                          st === "failed"
                            ? "text-red-300"
                            : st === "awaiting_approval"
                              ? "text-amber-300"
                              : "text-emerald-300/90"
                        }`}
                        title={mini[step.id]}
                      >
                        {mini[step.id]}
                      </p>
                    ) : null}
                    {st === "running" && (
                      <p className="mt-1 flex items-center gap-1 text-[9px] text-sky-300">
                        <Play className="h-2.5 w-2.5" /> live
                      </p>
                    )}
                    {st === "awaiting_approval" && (
                      <p className="mt-1 flex items-center gap-1 text-[9px] text-amber-300">
                        <Pause className="h-2.5 w-2.5" /> approval
                      </p>
                    )}
                    {st === "failed" && !mini[step.id] && (
                      <p className="mt-1 text-[9px] text-red-300">failed</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </main>

        {/* Inspector — resizable */}
        <aside
          className="relative flex shrink-0 flex-col border-l border-white/10 bg-[#10141c]"
          style={{ width: inspectorW }}
        >
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize inspector"
            title="Drag to resize inspector"
            className="absolute inset-y-0 left-0 z-20 w-1.5 cursor-col-resize hover:bg-cyan-400/40 active:bg-cyan-400/60"
            onMouseDown={(e) => {
              e.preventDefault();
              resizeStart.current = {
                x: e.clientX,
                w: inspectorW,
                kind: "inspector",
              };
              setResizingInspector(true);
            }}
          />
          <div className="border-b border-white/10 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
              Inspector
            </p>
            <p className="text-[9px] text-zinc-600">Drag left edge to resize</p>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-3 text-zinc-200">
            {selectedEdgeKey ? (
              <>
                <p className="text-xs font-medium text-cyan-200">Wire selected</p>
                <p className="break-all font-mono text-[10px] text-zinc-500">
                  {selectedEdgeKey}
                </p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="w-full"
                  onClick={() => {
                    const [ft, kind] = selectedEdgeKey.split(":");
                    const [from, to] = ft.split("->");
                    removeEdge(from, to, kind || "success");
                  }}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Disconnect wire
                </Button>
              </>
            ) : !selectedStep ? (
              <p className="text-sm text-zinc-500">
                Click a block to edit. Drag the <strong className="text-zinc-300">right port</strong> to
                another block&apos;s <strong className="text-zinc-300">left port</strong> to connect.
                Pan the board with <strong className="text-zinc-300">Space+drag</strong>, middle-mouse,
                or trackpad scroll.
              </p>
            ) : (
              <>
                <div>
                  <label className="text-[9px] uppercase text-zinc-500">Name</label>
                  <Input
                    className="mt-1 border-white/10 bg-black/30 text-sm"
                    value={selectedStep.name}
                    onChange={(e) =>
                      patchStep(selectedStep.id, { name: e.target.value })
                    }
                  />
                </div>
                <p className="break-all font-mono text-[10px] text-zinc-500">
                  {selectedStep.uses}
                </p>
                {selectedStep.uses === "apxv:handoff" && (
                  <div className="space-y-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2">
                    <p className="text-[10px] font-semibold uppercase text-amber-200/90">
                      Handoff target (required)
                    </p>
                    <p className="text-[10px] text-zinc-400">
                      Pick another saved pipeline to run as the next stage
                      (swarm). Not a board wire — wires only order steps in
                      this composition.
                    </p>
                    <select
                      className="h-9 w-full rounded-lg border border-white/10 bg-black/40 px-2 text-xs text-zinc-100"
                      value={
                        String(
                          (selectedStep.config as { pipeline_id?: string } | undefined)
                            ?.pipeline_id ?? "",
                        )
                      }
                      onChange={(e) =>
                        patchStep(selectedStep.id, {
                          config: {
                            ...(selectedStep.config ?? {}),
                            pipeline_id: e.target.value || undefined,
                            run_child: true,
                          },
                        })
                      }
                    >
                      <option value="">— Select target pipeline —</option>
                      {(pipelinesQuery.data?.pipelines ?? [])
                        .filter((p) => p.id !== doc.id)
                        .map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name || p.id}
                          </option>
                        ))}
                    </select>
                  </div>
                )}
                {selectedStep.uses === "apxv:approve" && (
                  <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-2 text-[10px] text-zinc-400">
                    Run will pause here until you Approve on the Runs page.
                  </p>
                )}
                {selectedStep.uses === "apxv:loop" && (
                  <div className="space-y-1.5 rounded-lg border border-sky-500/30 bg-sky-500/10 p-2">
                    <p className="text-[10px] font-semibold uppercase text-sky-200/90">
                      Bounded loop
                    </p>
                    <label className="text-[9px] uppercase text-zinc-500">
                      max_iterations (1–20)
                    </label>
                    <Input
                      className="border-white/10 bg-black/30 text-xs"
                      type="number"
                      min={1}
                      max={20}
                      value={String(
                        (selectedStep.config as { max_iterations?: number } | undefined)
                          ?.max_iterations ?? 3,
                      )}
                      onChange={(e) =>
                        patchStep(selectedStep.id, {
                          config: {
                            ...(selectedStep.config ?? {}),
                            max_iterations: Math.max(
                              1,
                              Math.min(20, Number(e.target.value) || 3),
                            ),
                          },
                        })
                      }
                    />
                    <p className="text-[9px] text-zinc-500">
                      Wire this block into a cycle carefully. Runtime stops if the
                      cap is exceeded.
                    </p>
                  </div>
                )}
                {usesKind(selectedStep.uses) === "agent" && (
                  <div className="space-y-2 rounded-lg border border-violet-500/25 bg-violet-500/5 p-2">
                    <p className="text-[10px] font-semibold uppercase text-violet-200/90">
                      Attached packs
                    </p>
                    <p className="text-[9px] text-zinc-500">
                      Packs apply governance with this agent. Order matters;
                      first becomes primary pack_profile on save.
                    </p>
                    <div className="max-h-28 space-y-1 overflow-y-auto">
                      {(packsQuery.data?.packs ?? []).map((p) => {
                        const pid = `pack:${p.id}`;
                        const attached = selectedStep.attached_packs ?? [];
                        const on = attached.some(
                          (a) => a === pid || a === p.id,
                        );
                        return (
                          <label
                            key={p.id}
                            className="flex cursor-pointer items-center gap-2 text-[11px] text-zinc-300"
                          >
                            <Checkbox
                              checked={on}
                              onChange={(e) => {
                                const next = e.target.checked
                                  ? [...attached.filter((a) => a !== p.id && a !== pid), pid]
                                  : attached.filter((a) => a !== pid && a !== p.id);
                                patchStep(
                                  selectedStep.id,
                                  syncAttachedPacks({
                                    ...selectedStep,
                                    attached_packs: next,
                                  }),
                                );
                              }}
                            />
                            <span className="truncate">{p.name || p.id}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
                {usesKind(selectedStep.uses) === "pack" && (
                  <div className="space-y-1">
                    <label className="text-[9px] uppercase text-zinc-500">
                      Pack profile (optional)
                    </label>
                    <Input
                      className="border-white/10 bg-black/30 font-mono text-xs"
                      placeholder="e.g. apxv-pack-reference-redaction"
                      value={String(selectedStep.pack_profile ?? "")}
                      onChange={(e) =>
                        patchStep(selectedStep.id, {
                          pack_profile: e.target.value || undefined,
                        })
                      }
                    />
                  </div>
                )}
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <Checkbox
                    checked={selectedStep.enabled !== false}
                    onChange={(e) =>
                      patchStep(selectedStep.id, {
                        enabled: e.target.checked,
                      })
                    }
                  />
                  <span className="flex items-center gap-1.5 text-sm">
                    <Power className="h-3.5 w-3.5" />
                    Enabled
                  </span>
                </label>
                <Button
                  size="sm"
                  variant="secondary"
                  className="w-full border-red-500/30 text-red-200 hover:bg-red-500/10"
                  onClick={() => {
                    const hasWires = (doc.edges ?? []).some(
                      (ed) =>
                        ed.from === selectedStep.id || ed.to === selectedStep.id,
                    );
                    if (
                      hasWires &&
                      !window.confirm(
                        `Remove “${selectedStep.name}” and its wires?`,
                      )
                    ) {
                      return;
                    }
                    removeStep(selectedStep.id);
                    setRunBanner("Block removed from board");
                  }}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Remove from board
                </Button>
                <p className="text-[9px] text-zinc-600">
                  Tip: select a block and press Delete
                </p>
              </>
            )}
            <div className="border-t border-white/10 pt-3">
              <p className="mb-1 text-[9px] uppercase text-zinc-500">Run input</p>
              <Textarea
                rows={5}
                className="border-white/10 bg-black/30 font-mono text-[11px]"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
            </div>
          </div>
        </aside>

        {/* Ingredient sheet (progressive disclosure — author layer) */}
        {sheetBlock ? (
          <div
            className="absolute inset-y-0 right-0 z-40 flex bg-black/50"
            style={{ left: shelfW }}
            onClick={() => setSheetBlock(null)}
            role="presentation"
          >
            <div
              className="m-3 flex w-full max-w-md flex-col rounded-xl border border-white/15 bg-[#121820] shadow-2xl"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-label="Ingredient sheet"
            >
              <div className="flex items-start justify-between gap-3 border-b border-white/10 px-4 py-3">
                <div>
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-zinc-200">
                      {kindLabel(sheetBlock.kind)}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${maturityBadgeClass(maturityForUses(sheetBlock.uses))}`}
                    >
                      {maturityForUses(sheetBlock.uses)}
                    </span>
                  </div>
                  <h2 className="text-base font-semibold text-zinc-50">
                    {sheetBlock.title}
                  </h2>
                  <p className="mt-0.5 font-mono text-[11px] text-zinc-500">
                    {sheetBlock.uses}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSheetBlock(null)}
                >
                  Close
                </Button>
              </div>
              <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm text-zinc-300">
                <p className="leading-relaxed text-zinc-400">
                  {purposeForBlock(sheetBlock)}
                </p>
                <div className="rounded-lg border border-white/10 bg-black/30 p-3 text-[12px]">
                  <p className="mb-1 text-[9px] font-bold uppercase text-zinc-500">
                    How to use
                  </p>
                  <ol className="list-decimal space-y-1 pl-4 text-zinc-400">
                    <li>Review this building block</li>
                    <li>
                      Click <strong className="text-zinc-200">Add to board</strong>
                    </li>
                    <li>
                      Optional: wire ports (right → left); otherwise run order
                      follows document order
                    </li>
                    <li>Configure the step in the right inspector</li>
                  </ol>
                </div>
                {sheetBlock.kind === "pack" ? (
                  <div className="space-y-2">
                    <p className="text-[12px] text-zinc-400">
                      Packs apply governance and agent bindings. Day-to-day use
                      is Add to board; authoring lives in Studio.
                    </p>
                    <Button size="sm" variant="secondary" asChild>
                      <Link to="/studio" search={{ tab: "packs" }}>
                        Open Studio · Packs
                      </Link>
                    </Button>
                  </div>
                ) : null}
                {sheetBlock.uses === "apxv:handoff" ? (
                  <p className="text-[12px] text-amber-200/90">
                    After adding, select the block and choose a target pipeline
                    in the inspector before Run.
                  </p>
                ) : null}
              </div>
              <div className="flex gap-2 border-t border-white/10 px-4 py-3">
                <Button
                  className="flex-1"
                  onClick={() => {
                    addBlock(sheetBlock);
                    setSheetBlock(null);
                  }}
                >
                  <Plus className="mr-1 h-3.5 w-3.5" />
                  Add to board
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setSheetBlock(null)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
