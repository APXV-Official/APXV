/**
 * Trust hub — Verify, Audit, Governance as one destination.
 */
import {
  ActionGroup,
  Button,
  DataSurface,
  SectionHeader,
} from "@apxv/ui";
import { Link } from "@tanstack/react-router";
import { Scale, ScrollText, ShieldCheck } from "lucide-react";
import { PageShell } from "../components/PageShell";

const CARDS = [
  {
    to: "/verify" as const,
    title: "Verify",
    description: "Validate attestation proofs for artifacts and runs.",
    icon: ShieldCheck,
    search: { hash: undefined, job: undefined },
  },
  {
    to: "/audit" as const,
    title: "Audit",
    description: "Explore tamper-evident audit logs for this instance.",
    icon: ScrollText,
    search: undefined,
  },
  {
    to: "/governance" as const,
    title: "Governance",
    description: "Rules, workflows, knowledge, and change proposals.",
    icon: Scale,
    search: { tab: undefined, proposal: undefined },
  },
];

export function TrustPage() {
  return (
    <PageShell className="space-y-6">
      <SectionHeader title="Trust" />
      <p className="max-w-2xl text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
        Prove and inspect what ran. Verify proofs, browse the audit chain, and
        manage governance. Author Proof Profiles in Studio, bind on Workbench,
        confirm claims on Runs.
      </p>
      <DataSurface className="space-y-2 p-3.5 text-xs">
        <p className="text-sm font-medium">Proof loop</p>
        <p className="text-[hsl(var(--muted-foreground))]">
          Studio (Proofs) → Test → Promote → Workbench shelf → bind → Run → claim
          on Runs / artifact.
        </p>
        <ActionGroup className="gap-x-4">
          <Button asChild size="sm" variant="secondary">
            <Link to="/studio" search={{ tab: "proofs" }}>
              Open Studio · Proofs
            </Link>
          </Button>
          <Button asChild size="sm" variant="secondary">
            <Link to="/workshop" search={{ id: undefined, shelf: "proofs" }}>
              Workbench · Proofs
            </Link>
          </Button>
          <Button asChild size="sm" variant="secondary">
            <Link to="/jobs" search={{ id: undefined }}>
              Runs
            </Link>
          </Button>
        </ActionGroup>
      </DataSurface>
      <div className="grid gap-3 sm:grid-cols-3">
        {CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <DataSurface key={card.to} className="flex flex-col gap-3 p-4">
              <div className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 text-[hsl(var(--primary))]" />
                <h2 className="text-sm font-semibold">{card.title}</h2>
              </div>
              <p className="flex-1 text-xs text-[hsl(var(--muted-foreground))]">
                {card.description}
              </p>
              <ActionGroup>
                <Button asChild size="sm">
                  <Link to={card.to} search={card.search}>
                    Open {card.title}
                  </Link>
                </Button>
              </ActionGroup>
            </DataSurface>
          );
        })}
      </div>
      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        After an attested run, open Run detail or paste an artifact hash in{" "}
        <strong className="text-[hsl(var(--foreground))]">Verify</strong>.
      </p>
    </PageShell>
  );
}
