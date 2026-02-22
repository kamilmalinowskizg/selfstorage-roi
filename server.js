/**
 * Serwer proxy dla OpenAI API (omija CORS w przeglądarce).
 * Uruchom: npm start  →  aplikacja: http://127.0.0.1:3000
 */
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Zezwól na żądania z przeglądarki (Live Server 5500 lub ten serwer 3000)
app.use(cors({
  origin: ['http://127.0.0.1:5500', 'http://localhost:5500', 'http://127.0.0.1:3000', 'http://localhost:3000'],
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type']
}));
app.use(express.json({ limit: '20mb' }));

// Pliki statyczne (aplikacja)
app.use(express.static(__dirname));

// Proxy do OpenAI: klucz API z przeglądarki, żądanie przekazane do OpenAI
app.post('/api/openai/chat', async (req, res) => {
  const { apiKey, body } = req.body || {};
  if (!apiKey || !body) {
    return res.status(400).json({ error: 'Brak apiKey lub body w żądaniu.' });
  }
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json(data);
    }
    res.json(data);
  } catch (err) {
    console.error('OpenAI proxy error:', err);
    res.status(502).json({ error: err.message || 'Błąd połączenia z OpenAI' });
  }
});

app.listen(PORT, () => {
  console.log(`Serwer działa: http://127.0.0.1:${PORT}`);
  console.log('Otwórz tę adres w przeglądarce – wtedy AI (PDF, analiza) będzie działać bez błędu CORS.');
});
