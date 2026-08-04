// @ts-nocheck
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const apiUrl = "https://opbento.vercel.app/api/bento?n=Moin&g=moin-dbud&x=Moin_Sheikh09&l=moin-build&i=https%3A%2F%2Fwww.moinsheikh.in%2Fimage1.webp&p=https%3A%2F%2Fwww.moinsheikh.in%2F&z=5d512";

interface BentoResponse {
  url: string;
}

export const fetchBentoUrl = async (apiUrl: string): Promise<string> => {
  try {
    const response = await fetch(apiUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: BentoResponse = (await response.json()) as BentoResponse;
    return data.url;
  } catch (error) {
    console.error("Error fetching Bento URL:", error);
    throw error;
  }
};

const addCacheBuster = (url: string): string => {
  const parsed = new URL(url);
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  parsed.searchParams.set("ghcache", timestamp);
  return parsed.toString();
};

export const updateReadmeWithBentoUrl = async (
  readmePath: string = path.join(process.cwd(), "README.md"),
  imageUrl: string
): Promise<void> => {
  const content = await readFile(readmePath, "utf8");
  const updatedContent = content.replace(/!\[OpBento\]\(.*?\)/, `![OpBento](${imageUrl})`);

  if (updatedContent === content) {
    console.log("README already up to date.");
    return;
  }

  await writeFile(readmePath, updatedContent, "utf8");
  console.log(`Updated ${readmePath}`);
};

const main = async (): Promise<void> => {
  const bentoUrl = await fetchBentoUrl(apiUrl);
  const cacheBustedUrl = addCacheBuster(bentoUrl);
  const readmePath = process.env.README_PATH || path.join(process.cwd(), "README.md");
  await updateReadmeWithBentoUrl(readmePath, cacheBustedUrl);
};

await main();