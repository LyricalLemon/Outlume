const API_KEY = "xyikoqz0wjlrdyv1w8rx05jh:og1yrhau2c";

async function pingEtsy() {
  console.log("Attempting to connect to Etsy API v3...");
  
  try {
    const response = await fetch("https://api.etsy.com/v3/application/openapi-ping", {
      method: "GET",
      headers: {
        "x-api-key": API_KEY,
      },
    });

    if (response.ok) {
      const data = await response.json();
      console.log("\nSuccess! Connected to Etsy API.");
      console.log("Response Data:", JSON.stringify(data, null, 2));
    } else {
      console.error("\nConnection failed!");
      console.error("Status:", response.status, response.statusText);
      const text = await response.text();
      console.error("Error Response:", text);
    }
  } catch (error) {
    console.error("\nNetwork error occurred:", error.message);
  }
}

pingEtsy();
