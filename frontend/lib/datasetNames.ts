export function displayDatasetName(
  name: string | null | undefined,
  fallback = "Dataset",
): string {
  const cleaned =
    name
      ?.trim()
      .replace(/(^|[^A-Za-z0-9])raw(?=$|[^A-Za-z0-9])/gi, "$1")
      .replace(/^[\s_.-]+|[\s_.-]+$/g, "")
      .replace(/[\s_-]{2,}/g, " ")
      .trim() ?? "";

  return cleaned || fallback;
}
