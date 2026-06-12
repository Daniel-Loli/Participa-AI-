#!/usr/bin/env node
/**
 * Convierte logo_participa_ai.svg a JPEG y lo sube como foto de perfil de WhatsApp Business
 * usando la Facebook Resumable Upload API (requerida para profile_picture_handle).
 */
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");
const axios = require("axios");

const ROOT = path.join(__dirname, "..");
const SVG_PATH = path.join(ROOT, "logo_participa_ai.svg");
const JPG_PATH = path.join(ROOT, "logo_participa_ai.jpg");

const PHONE_NUMBER_ID = "1120558211147140";
const ACCESS_TOKEN =
  "EAAVXb4iNy8oBRkyn4FHYB8PWo62l2YDaZB2fmZCZCwVB0TmOGQ4xz46fvIhvH7h9KoAUZA8c7pVO6fuNVWuY6vzlHtJtD1khIQEnsUXzz0fU6V51drtpLDNrDsFEft7m35TwoKYB8NdOpgJo49UzrsT7wjNEUykLOZBSmZAMcuSO2O6dlYQJGsSvZBEkc6krAZDZD";
const API_VERSION = "v18.0";

async function svgToJpeg() {
  console.log("Paso 1: Convirtiendo SVG → JPEG 640x640...");
  await sharp(SVG_PATH).resize(640, 640).jpeg({ quality: 90 }).toFile(JPG_PATH);
  const size = fs.statSync(JPG_PATH).size;
  console.log(`  ✓ JPEG generado: ${JPG_PATH} (${(size / 1024).toFixed(1)} KB)`);
  return size;
}

async function getAppId() {
  console.log("Paso 2: Obteniendo App ID desde el token...");
  const url = `https://graph.facebook.com/${API_VERSION}/debug_token`;
  const res = await axios.get(url, {
    params: { input_token: ACCESS_TOKEN, access_token: ACCESS_TOKEN },
  });
  const appId = res.data.data.app_id;
  console.log(`  ✓ App ID: ${appId}`);
  return appId;
}

async function createUploadSession(appId, fileSize) {
  console.log("Paso 3: Creando sesión de carga reutilizable...");
  const url = `https://graph.facebook.com/${API_VERSION}/${appId}/uploads`;
  const res = await axios.post(url, null, {
    params: {
      file_name: "logo_participa_ai.jpg",
      file_length: fileSize,
      file_type: "image/jpeg",
      access_token: ACCESS_TOKEN,
    },
  });
  const sessionId = res.data.id;
  console.log(`  ✓ Sesión creada: ${sessionId}`);
  return sessionId;
}

async function uploadFile(sessionId) {
  console.log("Paso 4: Subiendo imagen a la sesión...");
  const fileBuffer = fs.readFileSync(JPG_PATH);
  const url = `https://graph.facebook.com/${API_VERSION}/${sessionId}`;
  const res = await axios.post(url, fileBuffer, {
    headers: {
      Authorization: `OAuth ${ACCESS_TOKEN}`,
      file_offset: "0",
      "Content-Type": "image/jpeg",
    },
    maxBodyLength: Infinity,
  });
  const handle = res.data.h;
  console.log(`  ✓ Handle obtenido: ${handle}`);
  return handle;
}

async function updateProfile(handle) {
  console.log("Paso 5: Actualizando foto de perfil de WhatsApp Business...");
  const url = `https://graph.facebook.com/${API_VERSION}/${PHONE_NUMBER_ID}/whatsapp_business_profile`;
  const res = await axios.post(
    url,
    { messaging_product: "whatsapp", profile_picture_handle: handle },
    {
      headers: {
        Authorization: `Bearer ${ACCESS_TOKEN}`,
        "Content-Type": "application/json",
      },
    }
  );
  console.log("  ✓ Respuesta:", JSON.stringify(res.data));
}

(async () => {
  try {
    const fileSize = await svgToJpeg();
    const appId = await getAppId();
    const sessionId = await createUploadSession(appId, fileSize);
    const handle = await uploadFile(sessionId);
    await updateProfile(handle);
    console.log("\n✅ Logo de Participa AI configurado como foto de perfil de WhatsApp.");
  } catch (err) {
    const detail = err.response ? JSON.stringify(err.response.data) : err.message;
    console.error("❌ Error en paso:", err.config?.url || "");
    console.error("   Detalle:", detail);
    process.exit(1);
  }
})();
