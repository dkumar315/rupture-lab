import { describe, expect, it } from "vitest";

import { localRequestPath } from "@/lib/request-target";

const invalidTargets = [
  "",
  `/${"a".repeat(2048)}`,
  "demo/products",
  "//example.com/products",
  "/demo/products#fragment",
  "/demo\\products",
  "/demo/%ZZ",
  "/demo/%FF",
  "/%2F%2Fexample.com/products",
  "/demo/%5Cproducts",
  "/demo/%3Fsegment",
  "/demo/%23fragment",
  "/demo/%00products",
  "/demo/%7Fproducts",
  "/demo/./products",
  "/demo/../products",
  "/demo/%2E%2E/products",
  "/_rupturelab",
  "/%5Frupturelab/fault",
];

describe("localRequestPath", () => {
  it.each(invalidTargets)("rejects unsafe target %s", (target) => {
    expect(() => localRequestPath(target)).toThrow();
  });

  it("returns the decoded path while keeping query data out of fault matching", () => {
    expect(localRequestPath("/demo/%70roducts?tag=one&tag=two")).toBe(
      "/demo/products",
    );
  });
});
