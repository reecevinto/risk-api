import http from 'k6/http';
import { sleep } from 'k6';

export default function () {
  const url = 'http://host.docker.internal:8000/risk/score';

  const payload = JSON.stringify({
    email: "test@test.com",
    ip: "8.8.8.8"
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': 'YOUR_API_KEY'
    },
  };

  http.post(url, payload, params);
  sleep(1);
}