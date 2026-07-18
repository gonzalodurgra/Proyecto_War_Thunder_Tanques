"""
Motor de simulación de combate War Thunder.
Combina simulación Monte Carlo basada en reglas balísticas con una red neuronal
PyTorch que refina la efectividad de cada vehículo.
"""

from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - optional dependency in local dev
    torch = None
    nn = None

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover - optional dependency in local dev
    ort = None

if nn is None:
    class _TorchFallbackModule:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("PyTorch no está instalado. Usa el modelo ONNX o instala torch.")

        def eval(self) -> "_TorchFallbackModule":
            return self

        def train(self) -> "_TorchFallbackModule":
            return self

    class _TorchFallbackSequential:
        def __init__(self, *layers: Any) -> None:
            self.layers = layers

        def __call__(self, x: Any) -> Any:
            raise RuntimeError("PyTorch no está instalado. Usa el modelo ONNX o instala torch.")

    class _TorchFallbackOptimizer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def zero_grad(self) -> None:
            return None

        def step(self) -> None:
            return None

    class _TorchFallbackLoss:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("PyTorch no está instalado. Usa el modelo ONNX o instala torch.")

    nn = SimpleNamespace(
        Module=_TorchFallbackModule,
        Sequential=_TorchFallbackSequential,
        Linear=lambda *args, **kwargs: _TorchFallbackModule(),
        ReLU=lambda *args, **kwargs: _TorchFallbackModule(),
        MSELoss=_TorchFallbackLoss,
        Adam=_TorchFallbackOptimizer,
    )

BASE_DIR = Path(__file__).resolve().parent
DISTANCIAS_REF = [0, 100, 500, 1000, 1500, 2000]
MODELO_PATH = Path(os.getenv("COMBAT_MODEL_PT_PATH", str(BASE_DIR / "combat_model.pt")))
MODELO_ONNX_PATH = Path(os.getenv("COMBAT_MODEL_ONNX_PATH", str(BASE_DIR / "combat_model.onnx")))
SLOPE_FACTOR = 1.35
MC_DUELO_ITERACIONES = 2000
MC_EQUIPO_ITERACIONES = 800
MC_PAREJA_ITERACIONES = 400


@dataclass
class MunicionOptima:
    nombre: str
    tipo: str
    nombre_arma: str
    penetracion_mm: float
    dano_esperado: float
    masa_explosivo: float = 0.0


@dataclass
class PerfilCombate:
    nombre: str
    nacion: str
    br: float
    blindaje_chasis: float
    blindaje_torreta: float
    blindaje_efectivo: float
    velocidad: float
    intervalo_disparo: float
    cargador: int
    cadencia: float
    recarga: float
    municion_optima: MunicionOptima
    velocidad_torreta: float
    angulo_elevacion_max: float
    angulo_depresion_max: float
    tripulacion: float
    tiempo_apuntado_base: float
    supervivencia_base: float
    modificadores: Tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class ResultadoDuelo:
    ganador: str
    perdedor: str
    prob_victoria_ganador: float
    prob_victoria_v1: float
    prob_victoria_v2: float
    distancia_m: int
    simulaciones: int
    tiempo_medio_victoria_s: float
    municion_v1: MunicionOptima
    municion_v2: MunicionOptima
    detalles_v1: Dict[str, Any]
    detalles_v2: Dict[str, Any]
    resumen_tecnico: str


@dataclass
class ElementoClasificado:
    nombre: str
    nacion: str
    razon: str
    score: float = 0.0


@dataclass
class ResultadoEquipos:
    probabilidad_victoria: float
    simulaciones: int
    distancia_m: int
    aliados_vivos_media: float
    enemigos_vivos_media: float
    enemigos_prioritarios: List[ElementoClasificado]
    enemigos_a_evitar: List[ElementoClasificado]
    no_representan_amenaza: List[ElementoClasificado]
    mas_daninos: List[ElementoClasificado]
    mejores_companeros: List[ElementoClasificado]
    duelos_usuario: List[Dict[str, Any]]
    resumen_batalla: str


class CombatEffectivenessNet(nn.Module):
    """Red neuronal que refina multiplicadores de penetración, daño y supervivencia."""

    INPUT_DIM = 15

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(self.INPUT_DIM, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 3),
        )

    def forward(self, x: Any) -> Any:
        if torch is None:
            raise RuntimeError("PyTorch no está disponible; usa ONNX Runtime para inferencia.")
        return 0.75 + 0.5 * torch.sigmoid(self.encoder(x))


class CombatSimulatorEngine:
    def __init__(self) -> None:
        if torch is not None:
            self.device = torch.device("cpu")
            # only call .to() when torch is available
            self.net = CombatEffectivenessNet().to(self.device)
        else:
            self.device = None
            self.net = CombatEffectivenessNet()
        self.net.eval()
        self._model_ready = False
        self.onnx_session = None

    @staticmethod
    def _resolve_model_path(path: Path) -> Path:
        if path.is_absolute():
            return path
        candidates = [BASE_DIR / path, Path.cwd() / path]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def ensure_model_ready(self) -> None:
        if self._model_ready:
            return

        onnx_model_path = self._resolve_model_path(MODELO_ONNX_PATH)
        pt_model_path = self._resolve_model_path(MODELO_PATH)

        if onnx_model_path.exists() and ort is not None:
            try:
                self.onnx_session = ort.InferenceSession(str(onnx_model_path), providers=["CPUExecutionProvider"])
                self._model_ready = True
                return
            except Exception as exc:
                self.onnx_session = None
                print(f"Advertencia: no se pudo cargar el modelo ONNX {onnx_model_path}: {exc}")

        if pt_model_path.exists() and torch is not None:
            try:
                self.net.load_state_dict(torch.load(pt_model_path, map_location=self.device))
                self._model_ready = True
                return
            except Exception as exc:
                print(f"Advertencia: no se pudo cargar el modelo PyTorch {pt_model_path}: {exc}")

        if torch is None and ort is None:
            print("Advertencia: no hay PyTorch ni ONNX Runtime disponible; usando heurística simple.")
            self._model_ready = True
            return

        if torch is None:
            print("Advertencia: PyTorch no está instalado; usando heurística simple.")
            self._model_ready = True
            return

        self._bootstrap_train()
        self._model_ready = True

    def _bootstrap_train(self) -> None:
        """Entrena la red con pares sintéticos calibrados contra Monte Carlo puro."""
        if torch is None:
            return

        self.net.train()
        optimizer = torch.optim.Adam(self.net.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()

        for _ in range(40):
            features = []
            targets = []
            for _ in range(32):
                fake_tank = self._tanque_sintetico()
                feat = self._vector_caracteristicas(fake_tank, distancia=random.choice(DISTANCIAS_REF))
                mc_mods = self._modificadores_monte_carlo_puro(fake_tank, distancia=feat[-1] * 2000)
                features.append(feat)
                targets.append(mc_mods)

            x = torch.tensor(features, dtype=torch.float32, device=self.device)
            y = torch.tensor(targets, dtype=torch.float32, device=self.device)
            pred = self.net(x)
            loss = loss_fn(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        self.net.eval()
        try:
            torch.save(self.net.state_dict(), MODELO_PATH)
        except OSError:
            pass

    @staticmethod
    def _tanque_sintetico() -> Dict[str, Any]:
        pen = random.uniform(50, 350)
        return {
            "nombre": "Synth",
            "nacion": "Test",
            "rating_realista": random.uniform(1.0, 11.0),
            "blindaje_chasis": random.randint(10, 250),
            "blindaje_torreta": random.randint(10, 300),
            "velocidad_adelante_realista": random.randint(15, 75),
            "recarga": random.uniform(3, 12),
            "cadencia": random.uniform(5, 20),
            "cargador": random.choice([1, 1, 1, 3, 5, 8]),
            "velocidad_torreta": random.uniform(15, 60),
            "angulo_elevacion_max": random.uniform(20, 40),
            "angulo_depresion_max": random.uniform(5, 20),
            "tripulacion": random.uniform(0.6, 1.0),
            "setup_1": {
                "cañon": {
                    "municiones": [{
                        "nombre": "M61",
                        "tipo": random.choice(["APHE", "APDS", "HEATFS", "APCR"]),
                        "penetracion_mm": [
                            pen,
                            pen * 0.98,
                            pen * 0.92,
                            pen * 0.85,
                            pen * 0.78,
                            pen * 0.70,
                        ],
                        "masa_explosivo": random.uniform(0, 8000),
                        "masa_total": random.uniform(1000, 12000),
                    }]
                }
            },
        }
    @staticmethod
    def _modificadores_monte_carlo_puro(tanque: Dict[str, Any], distancia: float) -> List[float]:
        br = float(tanque.get("rating_realista") or 5)
        armor = max(
            float(tanque.get("blindaje_chasis") or 0),
            float(tanque.get("blindaje_torreta") or 0),
        )
        speed = float(tanque.get("velocidad_adelante_realista") or 30)
        pen = obtener_penetracion_maxima(tanque, int(distancia)).penetracion_mm
        dpm = calcular_dpm(tanque, int(distancia))

        pen_mod = min(1.25, max(0.75, pen / max(armor, 1) / 2.5))
        dmg_mod = min(1.25, max(0.75, dpm / 4000))
        surv_mod = min(1.25, max(0.75, (armor / 150 + speed / 60 + (10 - br) / 20) / 3))
        return [pen_mod, dmg_mod, surv_mod]

    def _vector_caracteristicas(self, tanque: Dict[str, Any], distancia: int) -> List[float]:
        br = float(tanque.get("rating_realista") or 5) / 12.0
        armor = max(
            float(tanque.get("blindaje_chasis") or 0),
            float(tanque.get("blindaje_torreta") or 0),
        ) / 350.0
        speed = float(tanque.get("velocidad_adelante_realista") or 0) / 80.0
        recarga = float(tanque.get("recarga") or 5) / 20.0
        cadencia = float(tanque.get("cadencia") or 0) / 30.0
        cargador = min(float(tanque.get("cargador") or 1), 10) / 10.0
        municion = obtener_penetracion_maxima(tanque, distancia)
        pen = municion.penetracion_mm / 400.0
        dano = municion.dano_esperado
        explosivo = municion.masa_explosivo / 10000.0
        dpm = calcular_dpm(tanque, distancia) / 8000.0
        dist_norm = distancia / 2000.0
        return [br, armor, speed, recarga, cadencia, cargador, pen, dano, explosivo, dpm, dist_norm,
                armor * 0.8, speed * 0.5, pen * dano, recarga * cadencia]

    def obtener_modificadores(self, tanque: Dict[str, Any], distancia: int) -> Tuple[float, float, float]:
        self.ensure_model_ready()
        feat = self._vector_caracteristicas(tanque, distancia)
        if self.onnx_session is not None:
            input_name = self.onnx_session.get_inputs()[0].name
            outputs = self.onnx_session.run(None, {input_name: np.array([feat], dtype=np.float32)})
            mods = outputs[0][0].tolist()
        elif torch is not None:
            with torch.no_grad():
                mods = self.net(torch.tensor([feat], dtype=torch.float32, device=self.device))[0].tolist()
        else:
            mods = self._modificadores_monte_carlo_puro(tanque, distancia=feat[-1] * 2000)
        return mods[0], mods[1], mods[2]

    def construir_perfil(
        self,
        tanque: Dict[str, Any],
        distancia: int,
        blindaje_objetivo: Optional[float] = None,
    ) -> PerfilCombate:
        mods = self.obtener_modificadores(tanque, distancia)
        municion = obtener_penetracion_maxima(tanque, distancia, blindaje_objetivo)
        blindaje = max(
            float(tanque.get("blindaje_chasis") or 0),
            float(tanque.get("blindaje_torreta") or 0),
        )
        velocidad_torreta = float(tanque.get("velocidad_torreta") or tanque.get("rotacion_torreta") or 30)
        angulo_elevacion_max = float(tanque.get("angulo_elevacion_max") or 30)
        angulo_depresion_max = float(tanque.get("angulo_depresion_max") or 10)
        tripulacion = min(max(float(tanque.get("tripulacion") or 0.75), 0.4), 1.0)
        tiempo_apuntado_base = max(0.5, 4.0 / max(velocidad_torreta, 1.0) + (30 - angulo_elevacion_max) * 0.02 + (15 - angulo_depresion_max) * 0.02)
        supervivencia_base = max(0.8, 0.8 + (blindaje / 300.0) * 0.6 + (tripulacion - 0.5) * 0.4)
        return PerfilCombate(
            nombre=tanque.get("nombre", "Desconocido"),
            nacion=tanque.get("nacion", "N/A"),
            br=float(tanque.get("rating_realista") or 0),
            blindaje_chasis=float(tanque.get("blindaje_chasis") or 0),
            blindaje_torreta=float(tanque.get("blindaje_torreta") or 0),
            blindaje_efectivo=blindaje * SLOPE_FACTOR,
            velocidad=float(tanque.get("velocidad_adelante_realista") or 0),
            intervalo_disparo=intervalo_disparo(tanque),
            cargador=int(tanque.get("cargador") or 1),
            cadencia=float(tanque.get("cadencia") or 0),
            recarga=float(tanque.get("recarga") or 5),
            municion_optima=municion,
            velocidad_torreta=velocidad_torreta,
            angulo_elevacion_max=angulo_elevacion_max,
            angulo_depresion_max=angulo_depresion_max,
            tripulacion=tripulacion,
            tiempo_apuntado_base=tiempo_apuntado_base,
            supervivencia_base=supervivencia_base,
            modificadores=mods,
        )


_engine: Optional[CombatSimulatorEngine] = None


def get_engine() -> CombatSimulatorEngine:
    global _engine
    if _engine is None:
        _engine = CombatSimulatorEngine()
    return _engine


def parse_distancia_combate(situacion: str) -> int:
    texto = situacion.lower()
    km_match = re.search(r"(\d+(?:[.,]\d+)?)\s*km", texto)
    if km_match:
        return min(2000, int(float(km_match.group(1).replace(",", ".")) * 1000))
    m_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m(?:etros|ts)?(?:\b|$)", texto)
    if m_match:
        return min(2000, int(float(m_match.group(1).replace(",", "."))))
    if any(x in texto for x in ("cqb", "corto", "urbano", "ciudad")):
        return 100
    if "medio" in texto or "intermedio" in texto:
        return 800
    if any(x in texto for x in ("largo", "snip", "campo abierto")):
        return 1500
    return 500


def penetracion_a_distancia(penetracion_mm: List[float], distancia: int) -> float:
    if not penetracion_mm:
        return 0.0
    valores = [float(v) for v in penetracion_mm[:6]]
    while len(valores) < 6:
        valores.append(valores[-1] if valores else 0.0)
    if distancia <= DISTANCIAS_REF[0]:
        return valores[0]
    if distancia >= DISTANCIAS_REF[-1]:
        return valores[-1]
    for i in range(len(DISTANCIAS_REF) - 1):
        d0, d1 = DISTANCIAS_REF[i], DISTANCIAS_REF[i + 1]
        if d0 <= distancia <= d1:
            t = (distancia - d0) / (d1 - d0)
            return valores[i] + t * (valores[i + 1] - valores[i])
    return valores[-1]


def intervalo_disparo(tanque: Dict[str, Any]) -> float:
    cargador = int(tanque.get("cargador") or 1)
    if cargador > 1:
        cadencia = float(tanque.get("cadencia") or 1)
        return 60.0 / max(cadencia, 1.0)
    return float(tanque.get("recarga") or 5.0)


def _es_municion_aphe(tipo: str) -> bool:
    """APHE, APHEBC y APHECBC comparten el prefijo APHE."""
    return "APHE" in tipo


def _es_municion_he_pura(tipo: str) -> bool:
    """HE de fragmentación sin capacidad de penetración tipo AP."""
    if "HEAT" in tipo or _es_municion_aphe(tipo):
        return False
    return tipo == "HE" or tipo.startswith("HE-")


def calcular_dano_proyectil(municion: Dict[str, Any], penetracion: float, blindaje: float) -> float:
    if penetracion < blindaje * 0.82:
        return 0.0
    tipo = str(municion.get("tipo", "")).upper()
    masa_exp = float(municion.get("masa_explosivo") or 0)
    masa_total = float(municion.get("masa_total") or 1000)
    factor_pen = min(1.0, penetracion / max(blindaje, 1))

    if _es_municion_aphe(tipo):
        # Mayor daño post-penetración: explosivo detonando tras atravesar el blindaje
        base = 0.48 + min(0.52, masa_exp / 3000) + min(0.22, masa_total / 11000)
    elif "HEAT" in tipo:
        base = 0.45 + min(0.55, masa_exp / 2800)
    elif _es_municion_he_pura(tipo):
        base = 0.25 + min(0.75, masa_exp / 4500)
    elif "APCR" in tipo or "APDS" in tipo:
        base = 0.30 + min(0.45, masa_total / 9000)
    else:
        base = 0.35 + min(0.45, masa_exp / 3800) + min(0.12, masa_total / 14000)
    return min(1.0, base * (0.65 + 0.35 * factor_pen))


def iterar_municiones(tanque: Dict[str, Any]):
    fuentes = []
    if "armamento" in tanque:
        fuentes.append(tanque["armamento"])
    for key, setup in tanque.items():
        if key.startswith("setup_") and isinstance(setup, dict):
            fuentes.append(setup)
    for armamento in fuentes:
        for nombre_arma, datos_arma in armamento.items():
            if not isinstance(datos_arma, dict):
                continue
            for municion in datos_arma.get("municiones", []):
                if isinstance(municion, dict):
                    yield nombre_arma, municion


def obtener_penetracion_maxima(
    tanque: Dict[str, Any],
    distancia: int,
    blindaje_objetivo: Optional[float] = None,
) -> MunicionOptima:
    mejor = MunicionOptima("N/A", "N/A", "N/A", 0.0, 0.0, 0.0)
    blindaje_referencia = blindaje_objetivo
    if blindaje_referencia is None:
        blindaje_referencia = max(
            float(tanque.get("blindaje_chasis") or 0),
            float(tanque.get("blindaje_torreta") or 0),
        ) * SLOPE_FACTOR

    for nombre_arma, municion in iterar_municiones(tanque):
        pen_list = municion.get("penetracion_mm") or []
        if not pen_list:
            continue
        pen = penetracion_a_distancia(pen_list, distancia)
        dano = calcular_dano_proyectil(municion, pen, max(blindaje_referencia, 80))
        score = dano * 100 + (pen if pen >= blindaje_referencia * 0.85 else pen * 0.35)
        mejor_score = mejor.dano_esperado * 100 + (
            mejor.penetracion_mm if mejor.penetracion_mm >= blindaje_referencia * 0.85
            else mejor.penetracion_mm * 0.35
        )
        if score > mejor_score:
            mejor = MunicionOptima(
                nombre=municion.get("nombre", "N/A"),
                tipo=municion.get("tipo", "N/A"),
                nombre_arma=nombre_arma,
                penetracion_mm=pen,
                dano_esperado=dano,
                masa_explosivo=float(municion.get("masa_explosivo") or 0),
            )
    return mejor


def calcular_dpm(tanque: Dict[str, Any], distancia: int) -> float:
    municion = obtener_penetracion_maxima(tanque, distancia)
    cadencia = float(tanque.get("cadencia") or 1.0)
    recarga = float(tanque.get("recarga") or 5.0)
    cargador = int(tanque.get("cargador") or 1)
    dano = max(municion.dano_esperado, 0.05)

    if cargador > 1:
        intervalo_entre_disparos = 60.0 / max(cadencia, 1.0)
        ciclo = cargador * intervalo_entre_disparos + max(recarga, 0.8)
        disparos_por_min = cargador * 60.0 / max(ciclo, 1.0)
    else:
        disparos_por_min = 60.0 / max(recarga, 0.5)

    return disparos_por_min * dano * 100


def _tiempo_de_apuntado(atacante: PerfilCombate, distancia: int, rng: random.Random) -> float:
    distancia_factor = 1.0 + min(max(distancia / 1500.0, 0.0), 0.5)
    turret_speed_penalty = max(0.9, 1.0 + (45.0 - atacante.velocidad_torreta) / 120.0)
    elevation_penalty = 1.0 + max(0.0, (25.0 - atacante.angulo_elevacion_max) / 80.0 + (12.0 - atacante.angulo_depresion_max) / 140.0)
    crew_penalty = 1.0 + (1.0 - atacante.tripulacion) * 0.35
    ruido = rng.uniform(0.85, 1.15)
    return max(0.35, atacante.tiempo_apuntado_base * distancia_factor * turret_speed_penalty * elevation_penalty * crew_penalty * ruido)


def _prob_penetracion(pen: float, blindaje: float, pen_mod: float, rng: random.Random) -> bool:
    angulo = rng.uniform(0.88, 1.45)
    umbral = blindaje * angulo / max(pen_mod, 0.1)
    if pen >= umbral:
        return True
    ratio = pen / max(umbral, 1)
    return rng.random() < max(0.05, min(0.92, ratio ** 1.4))


def _simular_disparo(
    atacante: PerfilCombate,
    defensor: PerfilCombate,
    rng: random.Random,
) -> float:
    pen = atacante.municion_optima.penetracion_mm * atacante.modificadores[0]
    if not _prob_penetracion(pen, defensor.blindaje_efectivo, 1.0, rng):
        return 0.0
    dano = atacante.municion_optima.dano_esperado * atacante.modificadores[1]
    supervivencia = max(defensor.modificadores[2] * defensor.supervivencia_base, 0.6)
    dano /= supervivencia
    variacion = rng.uniform(0.75, 1.25)
    return min(1.0, dano * variacion)


def _simular_duelo_unico(
    perfil_a: PerfilCombate,
    perfil_b: PerfilCombate,
    distancia: int,
    rng: random.Random,
    max_tiempo: float = 120.0,
) -> Tuple[str, float]:
    hp_a, hp_b = 1.0, 1.0
    t = 0.0
    next_a = _tiempo_de_apuntado(perfil_a, distancia, rng)
    next_b = _tiempo_de_apuntado(perfil_b, distancia, rng) * rng.uniform(0.8, 1.2)
    rounds_a = perfil_a.cargador
    rounds_b = perfil_b.cargador

    while t < max_tiempo and hp_a > 0 and hp_b > 0:
        if t >= next_a and hp_b > 0:
            if rounds_a <= 0:
                rounds_a = perfil_a.cargador
                next_a = t + max(perfil_a.recarga * rng.uniform(0.85, 1.15), 1.0)
            else:
                hp_b -= _simular_disparo(perfil_a, perfil_b, rng)
                rounds_a -= 1
                intervalo = perfil_a.intervalo_disparo
                aim_penalty = _tiempo_de_apuntado(perfil_a, distancia, rng)
                next_a = t + max(intervalo, aim_penalty)

        if t >= next_b and hp_a > 0:
            if rounds_b <= 0:
                rounds_b = perfil_b.cargador
                next_b = t + max(perfil_b.recarga * rng.uniform(0.85, 1.15), 1.0)
            else:
                hp_a -= _simular_disparo(perfil_b, perfil_a, rng)
                rounds_b -= 1
                intervalo = perfil_b.intervalo_disparo
                aim_penalty = _tiempo_de_apuntado(perfil_b, distancia, rng)
                next_b = t + max(intervalo, aim_penalty)

        t += 0.05

    if hp_a <= 0 and hp_b <= 0:
        ganador = perfil_a.nombre if rng.random() < 0.5 else perfil_b.nombre
    elif hp_b <= 0:
        ganador = perfil_a.nombre
    elif hp_a <= 0:
        ganador = perfil_b.nombre
    else:
        ganador = perfil_a.nombre if hp_a > hp_b else perfil_b.nombre
    return ganador, t


def simular_duelo_monte_carlo(
    tanque1: Dict[str, Any],
    tanque2: Dict[str, Any],
    situacion: str,
    n_simulaciones: int = MC_DUELO_ITERACIONES,
) -> ResultadoDuelo:
    engine = get_engine()
    distancia = parse_distancia_combate(situacion)
    blindaje_v2 = max(
        float(tanque2.get("blindaje_chasis") or 0),
        float(tanque2.get("blindaje_torreta") or 0),
    ) * SLOPE_FACTOR
    blindaje_v1 = max(
        float(tanque1.get("blindaje_chasis") or 0),
        float(tanque1.get("blindaje_torreta") or 0),
    ) * SLOPE_FACTOR
    p1 = engine.construir_perfil(tanque1, distancia, blindaje_v2)
    p2 = engine.construir_perfil(tanque2, distancia, blindaje_v1)

    rng = random.Random(hash((p1.nombre, p2.nombre, distancia)) & 0xFFFFFFFF)
    victorias = {p1.nombre: 0, p2.nombre: 0}
    tiempos: List[float] = []

    for _ in range(n_simulaciones):
        ganador, tiempo = _simular_duelo_unico(p1, p2, distancia, rng)
        victorias[ganador] += 1
        tiempos.append(tiempo)

    prob1 = victorias[p1.nombre] / n_simulaciones
    prob2 = victorias[p2.nombre] / n_simulaciones
    if prob1 >= prob2:
        ganador, perdedor, prob_g = p1.nombre, p2.nombre, prob1
    else:
        ganador, perdedor, prob_g = p2.nombre, p1.nombre, prob2

    detalles_v1 = _detalle_perfil(p1, p2, tanque1, distancia)
    detalles_v2 = _detalle_perfil(p2, p1, tanque2, distancia)
    resumen = (
        f"Duelo a {distancia}m: {p1.nombre} {prob1*100:.1f}% vs {p2.nombre} {prob2*100:.1f}%. "
        f"Ganador calculado: {ganador}. "
        f"Munición óptima V1: {p1.municion_optima.nombre} ({p1.municion_optima.penetracion_mm:.0f}mm). "
        f"Munición óptima V2: {p2.municion_optima.nombre} ({p2.municion_optima.penetracion_mm:.0f}mm)."
    )

    return ResultadoDuelo(
        ganador=ganador,
        perdedor=perdedor,
        prob_victoria_ganador=prob_g,
        prob_victoria_v1=prob1,
        prob_victoria_v2=prob2,
        distancia_m=distancia,
        simulaciones=n_simulaciones,
        tiempo_medio_victoria_s=sum(tiempos) / len(tiempos),
        municion_v1=p1.municion_optima,
        municion_v2=p2.municion_optima,
        detalles_v1=detalles_v1,
        detalles_v2=detalles_v2,
        resumen_tecnico=resumen,
    )


def _detalle_perfil(
    atacante: PerfilCombate,
    defensor: PerfilCombate,
    tanque: Dict[str, Any],
    distancia: int,
) -> Dict[str, Any]:
    pen = atacante.municion_optima.penetracion_mm
    puede_penetrar = pen >= defensor.blindaje_efectivo * 0.85
    return {
        "nombre": atacante.nombre,
        "nacion": atacante.nacion,
        "br": atacante.br,
        "blindaje_efectivo_mm": round(atacante.blindaje_efectivo, 1),
        "velocidad_kmh": atacante.velocidad,
        "intervalo_disparo_s": round(atacante.intervalo_disparo, 2),
        "cargador": atacante.cargador,
        "cadencia": atacante.cadencia,
        "recarga": atacante.recarga,
        "modificadores_nn": {
            "penetracion": round(atacante.modificadores[0], 3),
            "dano": round(atacante.modificadores[1], 3),
            "supervivencia": round(atacante.modificadores[2], 3),
        },
        "municion_optima": {
            "nombre": atacante.municion_optima.nombre,
            "tipo": atacante.municion_optima.tipo,
            "arma": atacante.municion_optima.nombre_arma,
            "penetracion_mm": round(pen, 1),
            "dano_esperado": round(atacante.municion_optima.dano_esperado, 3),
            "masa_explosivo_g": atacante.municion_optima.masa_explosivo,
        },
        "puede_penetrar_oponente": puede_penetrar,
        "dpm_estimado": round(calcular_dpm(tanque, distancia), 1),
    }


def _simular_pareja(
    tanque_a: Dict[str, Any],
    tanque_b: Dict[str, Any],
    distancia: int,
    n: int = MC_PAREJA_ITERACIONES,
) -> Dict[str, float]:
    engine = get_engine()
    pa = engine.construir_perfil(tanque_a, distancia, max(
        float(tanque_b.get("blindaje_chasis") or 0),
        float(tanque_b.get("blindaje_torreta") or 0),
    ) * SLOPE_FACTOR)
    pb = engine.construir_perfil(tanque_b, distancia, max(
        float(tanque_a.get("blindaje_chasis") or 0),
        float(tanque_a.get("blindaje_torreta") or 0),
    ) * SLOPE_FACTOR)
    rng = random.Random(hash((pa.nombre, pb.nombre, distancia, n)) & 0xFFFFFFFF)
    wins_a = 0
    dmg_to_b = 0.0
    dmg_to_a = 0.0

    for _ in range(n):
        hp_a, hp_b = 1.0, 1.0
        t = 0.0
        next_a, next_b = 0.0, pb.intervalo_disparo * 0.5
        while t < 90 and hp_a > 0 and hp_b > 0:
            if t >= next_a:
                d = _simular_disparo(pa, pb, rng)
                hp_b -= d
                dmg_to_b += d
                next_a = t + pa.intervalo_disparo
            if t >= next_b:
                d = _simular_disparo(pb, pa, rng)
                hp_a -= d
                dmg_to_a += d
                next_b = t + pb.intervalo_disparo
            t += 0.05
        if hp_b <= 0 and hp_a > 0:
            wins_a += 1
        elif hp_a <= 0 and hp_b > 0:
            pass
        elif hp_a > hp_b:
            wins_a += 1

    return {
        "prob_victoria_a": wins_a / n,
        "prob_victoria_b": 1 - wins_a / n,
        "dano_medio_a_inflige": dmg_to_b / n,
        "dano_medio_b_inflige": dmg_to_a / n,
        "puede_a_pen_b": pa.municion_optima.penetracion_mm >= pb.blindaje_efectivo * 0.85,
        "puede_b_pen_a": pb.municion_optima.penetracion_mm >= pa.blindaje_efectivo * 0.85,
    }


def simular_equipos_monte_carlo(
    equipo_aliado: List[Dict[str, Any]],
    equipo_enemigo: List[Dict[str, Any]],
    tanque_usuario_index: int,
    situacion: str,
    n_simulaciones: int = MC_EQUIPO_ITERACIONES,
) -> ResultadoEquipos:
    engine = get_engine()
    distancia = parse_distancia_combate(situacion)
    usuario = equipo_aliado[tanque_usuario_index]

    perfiles_aliados = [engine.construir_perfil(t, distancia) for t in equipo_aliado]
    perfiles_enemigos = [engine.construir_perfil(t, distancia) for t in equipo_enemigo]

    rng = random.Random(hash((distancia, len(equipo_aliado), len(equipo_enemigo))) & 0xFFFFFFFF)
    victorias_aliados = 0
    aliados_vivos_total = 0.0
    enemigos_vivos_total = 0.0

    for _ in range(n_simulaciones):
        hp_aliados = [1.0] * len(perfiles_aliados)
        hp_enemigos = [1.0] * len(perfiles_enemigos)
        timers_a = [rng.uniform(0, p.intervalo_disparo) for p in perfiles_aliados]
        timers_e = [rng.uniform(0, p.intervalo_disparo) for p in perfiles_enemigos]
        t = 0.0

        while t < 240 and any(h > 0 for h in hp_aliados) and any(h > 0 for h in hp_enemigos):
            for i, pa in enumerate(perfiles_aliados):
                if hp_aliados[i] <= 0 or t < timers_a[i]:
                    continue
                objetivos = [j for j, h in enumerate(hp_enemigos) if h > 0]
                if not objetivos:
                    break
                j = rng.choice(objetivos)
                hp_enemigos[j] -= _simular_disparo(pa, perfiles_enemigos[j], rng)
                timers_a[i] = t + pa.intervalo_disparo

            for j, pe in enumerate(perfiles_enemigos):
                if hp_enemigos[j] <= 0 or t < timers_e[j]:
                    continue
                objetivos = [i for i, h in enumerate(hp_aliados) if h > 0]
                if not objetivos:
                    break
                i = rng.choice(objetivos)
                hp_aliados[i] -= _simular_disparo(pe, perfiles_aliados[i], rng)
                timers_e[j] = t + pe.intervalo_disparo

            t += 0.1

        if not any(h > 0 for h in hp_enemigos):
            victorias_aliados += 1
        aliados_vivos_total += sum(1 for h in hp_aliados if h > 0)
        enemigos_vivos_total += sum(1 for h in hp_enemigos if h > 0)

    prob_victoria = (victorias_aliados / n_simulaciones) * 100.0
    duelos_usuario: List[Dict[str, Any]] = []

    for enemigo in equipo_enemigo:
        stats = _simular_pareja(usuario, enemigo, distancia)
        perfil_u = engine.construir_perfil(usuario, distancia)
        perfil_e = engine.construir_perfil(enemigo, distancia)
        duelos_usuario.append({
            "enemigo": enemigo.get("nombre"),
            "nacion": enemigo.get("nacion"),
            "prob_usuario_gana": stats["prob_victoria_a"],
            "prob_enemigo_gana": stats["prob_victoria_b"],
            "dano_usuario_inflige": stats["dano_medio_a_inflige"],
            "dano_enemigo_inflige": stats["dano_medio_b_inflige"],
            "puede_usuario_penetrar": stats["puede_a_pen_b"],
            "puede_enemigo_penetrar": stats["puede_b_pen_a"],
            "municion_usuario": perfil_u.municion_optima.nombre,
            "municion_enemigo": perfil_e.municion_optima.nombre,
        })

    clasificaciones = _clasificar_enemigos_usuario(usuario, equipo_aliado, duelos_usuario, tanque_usuario_index, distancia)

    resumen = (
        f"Batalla de equipos a {distancia}m ({n_simulaciones} simulaciones). "
        f"Probabilidad victoria aliados: {prob_victoria:.1f}%. "
        f"Promedio supervivientes: aliados {aliados_vivos_total/n_simulaciones:.1f}, "
        f"enemigos {enemigos_vivos_total/n_simulaciones:.1f}."
    )

    return ResultadoEquipos(
        probabilidad_victoria=round(prob_victoria, 1),
        simulaciones=n_simulaciones,
        distancia_m=distancia,
        aliados_vivos_media=round(aliados_vivos_total / n_simulaciones, 2),
        enemigos_vivos_media=round(enemigos_vivos_total / n_simulaciones, 2),
        enemigos_prioritarios=clasificaciones["prioritarios"],
        enemigos_a_evitar=clasificaciones["evitar"],
        no_representan_amenaza=clasificaciones["no_amenaza"],
        mas_daninos=clasificaciones["mas_daninos"],
        mejores_companeros=clasificaciones["companeros"],
        duelos_usuario=duelos_usuario,
        resumen_batalla=resumen,
    )


def _clasificar_enemigos_usuario(
    usuario: Dict[str, Any],
    aliados: List[Dict[str, Any]],
    duelos: List[Dict[str, Any]],
    usuario_idx: int,
    distancia: int,
) -> Dict[str, List[ElementoClasificado]]:
    prioritarios: List[ElementoClasificado] = []
    evitar: List[ElementoClasificado] = []
    no_amenaza: List[ElementoClasificado] = []
    mas_daninos: List[ElementoClasificado] = []

    for d in duelos:
        nombre = d["enemigo"]
        nacion = d["nacion"]
        p_user = d["prob_usuario_gana"]
        p_enemy = d["prob_enemigo_gana"]
        dano_enemy = d["dano_enemigo_inflige"]

        if not d["puede_enemigo_penetrar"] and dano_enemy < 0.25:
            no_amenaza.append(ElementoClasificado(
                nombre=nombre,
                nacion=nacion,
                score=1 - p_enemy,
                razon=(
                    f"Penetración insuficiente contra tu blindaje a {distancia}m "
                    f"({d['municion_enemigo']}). Prob. victoria enemiga: {p_enemy*100:.0f}%."
                ),
            ))
        if p_user >= 0.52 and d["puede_usuario_penetrar"]:
            prioritarios.append(ElementoClasificado(
                nombre=nombre,
                nacion=nacion,
                score=p_user,
                razon=(
                    f"Blanco favorable: tu {d['municion_usuario']} mantiene ventaja "
                    f"({p_user*100:.0f}% victoria en duelo simulado)."
                ),
            ))
        if p_enemy >= 0.52 and d["puede_enemigo_penetrar"]:
            evitar.append(ElementoClasificado(
                nombre=nombre,
                nacion=nacion,
                score=p_enemy,
                razon=(
                    f"Amenaza directa: {d['municion_enemigo']} supera tu blindaje "
                    f"({p_enemy*100:.0f}% victoria enemiga, daño medio {dano_enemy:.2f})."
                ),
            ))
        mas_daninos.append(ElementoClasificado(
            nombre=nombre,
            nacion=nacion,
            score=dano_enemy * p_enemy,
            razon=(
                f"Daño esperado combinado: {dano_enemy:.2f} por enfrentamiento "
                f"con {p_enemy*100:.0f}% prob. de derrota tuya."
            ),
        ))

    mas_daninos.sort(key=lambda x: x.score, reverse=True)
    mas_daninos = mas_daninos[: max(1, len(mas_daninos) // 2)]
    prioritarios.sort(key=lambda x: x.score, reverse=True)
    evitar.sort(key=lambda x: x.score, reverse=True)

    companeros = _evaluar_companeros(usuario, aliados, usuario_idx, distancia)

    return {
        "prioritarios": prioritarios[:5],
        "evitar": evitar[:5],
        "no_amenaza": no_amenaza[:5],
        "mas_daninos": mas_daninos[:5],
        "companeros": companeros[:5],
    }


def _evaluar_companeros(
    usuario: Dict[str, Any],
    aliados: List[Dict[str, Any]],
    usuario_idx: int,
    distancia: int,
) -> List[ElementoClasificado]:
    engine = get_engine()
    perfil_u = engine.construir_perfil(usuario, distancia)
    resultados: List[ElementoClasificado] = []

    for i, aliado in enumerate(aliados):
        if i == usuario_idx:
            continue
        perfil_a = engine.construir_perfil(aliado, distancia)
        pen_gap = perfil_a.municion_optima.penetracion_mm - perfil_u.municion_optima.penetracion_mm
        armor_gap = perfil_a.blindaje_efectivo - perfil_u.blindaje_efectivo
        speed_gap = perfil_a.velocidad - perfil_u.velocidad
        score = (
            max(0, pen_gap / 200) * 0.35
            + max(0, armor_gap / 150) * 0.35
            + max(0, speed_gap / 40) * 0.15
            + (1 / max(perfil_a.intervalo_disparo, 0.5)) * 0.15
        )
        razones = []
        if pen_gap > 20:
            razones.append(f"mayor penetración ({perfil_a.municion_optima.penetracion_mm:.0f}mm vs {perfil_u.municion_optima.penetracion_mm:.0f}mm)")
        if armor_gap > 15:
            razones.append(f"blindaje superior ({perfil_a.blindaje_efectivo:.0f}mm efectivos)")
        if speed_gap > 8:
            razones.append(f"movilidad para flanqueo (+{speed_gap:.0f} km/h)")
        if perfil_a.intervalo_disparo < perfil_u.intervalo_disparo:
            razones.append("cadencia/recarga más rápida para supresión")
        if not razones:
            razones.append("apoyo equilibrado en fuego y supervivencia")

        resultados.append(ElementoClasificado(
            nombre=aliado.get("nombre", "Aliado"),
            nacion=aliado.get("nacion", "N/A"),
            score=score,
            razon="Cooperación recomendada por: " + ", ".join(razones) + ".",
        ))

    resultados.sort(key=lambda x: x.score, reverse=True)
    return resultados


def resultado_duelo_a_dict(resultado: ResultadoDuelo) -> Dict[str, Any]:
    return {
        "ganador": resultado.ganador,
        "perdedor": resultado.perdedor,
        "prob_victoria_ganador_pct": round(resultado.prob_victoria_ganador * 100, 2),
        "prob_victoria_v1_pct": round(resultado.prob_victoria_v1 * 100, 2),
        "prob_victoria_v2_pct": round(resultado.prob_victoria_v2 * 100, 2),
        "distancia_m": resultado.distancia_m,
        "simulaciones_monte_carlo": resultado.simulaciones,
        "tiempo_medio_victoria_s": round(resultado.tiempo_medio_victoria_s, 1),
        "vehiculo_1": resultado.detalles_v1,
        "vehiculo_2": resultado.detalles_v2,
        "resumen_tecnico": resultado.resumen_tecnico,
    }


def resultado_equipos_a_dict(resultado: ResultadoEquipos) -> Dict[str, Any]:
    def _lista(items: List[ElementoClasificado]) -> List[Dict[str, str]]:
        return [{"nombre": e.nombre, "nacion": e.nacion, "razon": e.razon} for e in items]

    return {
        "probabilidad_victoria": resultado.probabilidad_victoria,
        "distancia_m": resultado.distancia_m,
        "simulaciones_monte_carlo": resultado.simulaciones,
        "aliados_vivos_media": resultado.aliados_vivos_media,
        "enemigos_vivos_media": resultado.enemigos_vivos_media,
        "enemigos_prioritarios": _lista(resultado.enemigos_prioritarios),
        "enemigos_a_evitar": _lista(resultado.enemigos_a_evitar),
        "no_representan_amenaza": _lista(resultado.no_representan_amenaza),
        "mas_daninos": _lista(resultado.mas_daninos),
        "mejores_companeros": _lista(resultado.mejores_companeros),
        "duelos_usuario_vs_enemigos": resultado.duelos_usuario,
        "resumen_batalla": resultado.resumen_batalla,
    }
