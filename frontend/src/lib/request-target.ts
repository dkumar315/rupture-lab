const invalidPercentEscape = /%(?![0-9A-Fa-f]{2})/;
const controlNamespace = "/_rupturelab";

function containsControlCharacter(value: string): boolean {
  return [...value].some((character) => {
    const code = character.charCodeAt(0);
    return code <= 0x1f || code === 0x7f;
  });
}

export function localRequestPath(target: string): string {
  if (target.length === 0 || target.length > 2048) {
    throw new Error("Path must contain between 1 and 2048 characters");
  }

  if (!target.startsWith("/") || target.startsWith("//")) {
    throw new Error(
      "Path must be a local request target starting with a single '/'",
    );
  }

  if (target.includes("#")) {
    throw new Error("Path must not contain a URL fragment");
  }

  const queryIndex = target.indexOf("?");
  const rawPath = queryIndex === -1 ? target : target.slice(0, queryIndex);

  if (rawPath.includes("\\") || invalidPercentEscape.test(rawPath)) {
    throw new Error("Path contains an invalid or ambiguous escape");
  }

  let decodedPath: string;

  try {
    decodedPath = decodeURIComponent(rawPath);
  } catch {
    throw new Error("Path contains invalid UTF-8 escaping");
  }

  if (decodedPath.startsWith("//") || decodedPath.includes("\\")) {
    throw new Error("Path must not contain an authority-like path");
  }

  if (decodedPath.includes("?") || decodedPath.includes("#")) {
    throw new Error("Path contains an encoded URL delimiter");
  }

  if (containsControlCharacter(decodedPath)) {
    throw new Error("Path must not contain control characters");
  }

  if (
    decodedPath
      .split("/")
      .some((segment) => segment === "." || segment === "..")
  ) {
    throw new Error("Path must not contain dot segments");
  }

  if (
    decodedPath === controlNamespace ||
    decodedPath.startsWith(`${controlNamespace}/`)
  ) {
    throw new Error(
      "Experiments cannot target the RuptureLab control namespace",
    );
  }

  return decodedPath;
}
