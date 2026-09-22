const API_BASE_URL = "http://127.0.0.1:8000/api";

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Login failed");
  }

  return data;
}

export async function getComputers() {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("Authentication token not found.");
  }

  const response = await fetch(`${API_BASE_URL}/clients`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch computers.");
  }

  return data;
}