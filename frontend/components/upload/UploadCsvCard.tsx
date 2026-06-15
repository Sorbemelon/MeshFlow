"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";

/**
 * Upload CSV card — UI states only. Phase 2 does not send files or fake any
 * success: selecting a file reveals the Upload affordance, which stays disabled
 * because validation + S3/Snowflake readiness are backend work (Phase 4).
 */
export function UploadCsvCard() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <Card>
      <CardHeader
        title="Upload CSV"
        description="MVP: one CSV file per dataset. Up to three files per dataset is planned for later."
      />

      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
      />

      <div className="rounded-md border border-dashed border-border bg-surface-muted px-4 py-6 text-center">
        {fileName ? (
          <p className="text-sm text-ink-soft">
            Selected: <span className="font-mono text-ink">{fileName}</span>
          </p>
        ) : (
          <p className="text-sm text-ink-muted">
            Choose a CSV file to begin. Nothing is uploaded yet.
          </p>
        )}

        <div className="mt-4 flex items-center justify-center gap-2">
          <Button
            variant={fileName ? "secondary" : "primary"}
            size="sm"
            onClick={() => inputRef.current?.click()}
          >
            Browse
          </Button>
          {fileName ? (
            <Button
              size="sm"
              disabled
              title="Upload runs after CSV validation and S3/Snowflake readiness checks (Phase 4)."
            >
              Upload
            </Button>
          ) : null}
        </div>
      </div>

      <p className="mt-3 text-xs text-ink-muted">
        On upload, MeshFlow validates the CSV and checks S3 + Snowflake readiness
        before any data is sent. Invalid files are rejected with a clear reason —
        no partial or fake success.
      </p>
    </Card>
  );
}
