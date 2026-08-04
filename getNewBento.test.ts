import { describe, expect, test } from "bun:test";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { updateReadmeWithBentoUrl } from "./getNewBento";

describe("updateReadmeWithBentoUrl", () => {
  test("replaces the existing OpBento image link in the README", async () => {
    const tempDir = await mkdtemp(path.join(tmpdir(), "opbento-"));
    const readmePath = path.join(tempDir, "README.md");

    await writeFile(
      readmePath,
      "![OpBento](https://old.example/image.png)\n",
      "utf8"
    );

    await updateReadmeWithBentoUrl(readmePath, "https://new.example/image.png");

    const updated = await Bun.file(readmePath).text();
    expect(updated).toContain("![OpBento](https://new.example/image.png)");
    expect(updated).not.toContain("https://old.example/image.png");

    await rm(tempDir, { recursive: true, force: true });
  });
});
