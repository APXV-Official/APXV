import type { VerificationReport } from "@apxv/api-client";
import type { ReactNode } from "react";
import {
  ActionGroup,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  SectionHeader,
  StatusDot,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@apxv/ui";
import { ZkProofVisualizer } from "./ZkProofVisualizer";
import { formatDisplayValue } from "../lib/format-value";
import { extractReportZkNodes } from "../lib/zk-utils";

function ReportSection({
  title,
  children,
  embedded,
}: {
  title: string;
  children: ReactNode;
  embedded?: boolean;
}) {
  if (embedded) {
    return (
      <section className="space-y-4 border-t border-[hsl(var(--divider))] pt-6">
        <SectionHeader title={title} />
        {children}
      </section>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function VerificationReportView({
  report,
  embedded = false,
}: {
  report: VerificationReport;
  embedded?: boolean;
}) {
  const python = report.python;
  const zkNodes = extractReportZkNodes(report.zk);

  return (
    <div className="space-y-4">
      {!embedded && (
        <ActionGroup>
          <span className="inline-flex items-center gap-2 text-sm">
            <StatusDot tone={report.overall_valid ? "success" : "destructive"} />
            {report.overall_valid ? "Valid" : "Invalid"}
          </span>
          {report.attestation_id && (
            <span className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
              {report.attestation_id}
            </span>
          )}
        </ActionGroup>
      )}

      <ReportSection title="Python verification" embedded={embedded}>
        <div className="mb-3 flex items-center gap-2">
          <Badge
            variant={
              python?.overall_status === "VERIFIED" ? "success" : "warning"
            }
          >
            {python?.overall_status ?? "—"}
          </Badge>
        </div>
        {(python?.checks ?? []).length === 0 ? (
          <EmptyState title="No Python checks returned" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Check</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {python?.checks?.map((check) => (
                <TableRow key={check.name}>
                  <TableCell className="font-mono">{check.name}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-2 text-sm">
                      <StatusDot tone={check.passed ? "success" : "destructive"} />
                      {check.passed ? "Pass" : "Fail"}
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-pre-wrap text-[hsl(var(--muted-foreground))]">
                    {formatDisplayValue(check.details)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </ReportSection>

      {report.zk && (
        <ReportSection title="Groth16 verification" embedded={embedded}>
          <ZkProofVisualizer nodes={zkNodes} />
        </ReportSection>
      )}
    </div>
  );
}