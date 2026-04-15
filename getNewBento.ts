const apiUrl = "https://opbento.vercel.app/api/bento?n=Moin&g=moin-dbud&x=Moin_Sheikh09&l=moin-build&i=https%3A%2F%2Fwww.moinsheikh.in%2Fprofile.jpeg&p=&z=301b6";
interface BentoResponse {
  url: string;
}

const fetchBentoUrl = async (apiUrl: string): Promise<string> => {
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

// @ts-ignore
await fetchBentoUrl(apiUrl);
