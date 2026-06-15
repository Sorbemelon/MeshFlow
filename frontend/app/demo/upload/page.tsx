import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { UploadCsvCard } from "@/components/upload/UploadCsvCard";

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Upload Dataset
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Start from the curated demo or bring your own CSV.
        </p>
      </header>

      <div className="grid gap-5 sm:grid-cols-2">
        {/* Raw Retail Transactions Demo */}
        <Card>
          <CardHeader
            title="Raw Retail Transactions Demo"
            description="A raw, denormalized transactions file — MeshFlow turns it into a Dimensional Model and Data Marts."
            action={<StatusBadge status="waiting" label="Not added" />}
          />
          <p className="text-sm leading-relaxed text-ink-soft">
            Curated for the demo. It can be added once per session.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button>Use Demo Dataset</Button>
            <Button href="/demo/data-flow" variant="secondary">
              Open Data Flow
            </Button>
          </div>
        </Card>

        {/* Upload CSV */}
        <UploadCsvCard />
      </div>

      {/* Available datasets summary */}
      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold text-ink">
          Available datasets
        </h2>
        <div className="rounded-lg border border-dashed border-border bg-surface px-5 py-8 text-center text-sm text-ink-muted">
          No datasets yet. Add the demo dataset or upload a CSV to get started.
        </div>
      </section>
    </div>
  );
}
