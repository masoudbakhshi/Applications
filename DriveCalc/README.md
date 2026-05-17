# DriveCalc: Electrical, Motor Control & Power Electronics Calculator

**Author:** Masoud Bakhshi

A practical engineering calculator covering motor control, power electronics, embedded firmware, thermal analysis, and EV propulsion. Built for engineers and students who need reliable, formula-based tools they can trust in real design work.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Sections

| Section | Calculators |
|---|---|
| **Unit Converters** | Electrical, motor-control, mechanical/vehicle, thermal |
| **Motor Control** | Speed & frequency, torque-power-speed, PMSM/IPMSM torque, EESM torque, dq voltage, field weakening, PI gain design, torque-speed envelope |
| **Power Electronics** | Inverter voltage (SPWM/SVPWM), SVPWM sector & duties, Buck, Boost, DC-link capacitor ripple |
| **Embedded / PWM** | PWM timer registers, minimum pulse width, dead-time error, discrete PI (Tustin/Euler), ADC scaling, Q-format, dB/gain, CPU load |
| **Thermal & Loss** | Copper loss, thermal rise (steady-state + transient), cable voltage drop & loss, semiconductor loss, thermal derating |
| **EV / Vehicle** | Battery power & current, tractive force & acceleration, road load, regen braking, 0–100 km/h simulation |
| **General Electrical** | Ohm's law, RC/RL/RLC circuits (+ Bode plot), power factor, impedance, filter design |
| **Formula Reference** | All formulas with derivations and engineering notes |

## Project Structure

```
DriveCalc/
├── app.py                   # Main Streamlit entry point
├── requirements.txt
├── README.md
├── calculators/
│   ├── unit_converters.py
│   ├── motor_control.py
│   ├── power_electronics.py
│   ├── embedded_pwm.py
│   ├── thermal.py
│   ├── vehicle.py
│   └── electrical.py
└── utils/
    ├── validation.py
    ├── formatting.py
    └── plotting.py
```

## Deployment

### Streamlit Community Cloud
1. Push to GitHub (public or private with access granted)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → set main file to `app.py`
4. Deploy

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Engineering Notes

- All formulas use SI units internally; unit conversions are performed at the display layer.
- dq-frame currents `id`, `iq` are **peak** values throughout, not RMS.
- PMSM torque formula: `Te = (3/2)·p·[ψ_f·iq + (Ld−Lq)·id·iq]`
- SVPWM voltage limit: `V_dc/√3` (vs `V_dc/2` for SPWM: 15.5% advantage)
- PI gains use bandwidth-based design: `Kp = L·ωc`, `Ki = Rs·ωc`
- All thermal calculations are simplified single-element RC models

## Validation Checks

| Test | Expected | Formula |
|---|---|---|
| 100 Nm × 3000 rpm | ≈ 31.4 kW | P = T·n/9549 |
| 3000 rpm | ≈ 314.16 rad/s | ω = 2π·n/60 |
| p=4, n=3000 rpm | f_e = 200 Hz | f_e = p·n/60 |
| Ld=1.5mH, ωc=2π·500 | Kp_d ≈ 4.712 | Kp = Ld·ωc |
| L=100µH, D=0.5, fsw=100kHz, Vin=48V | Vout=24V, ΔIL=1.2A | Buck CCM |
| P=100W, Rth=0.5 K/W, Tamb=40°C | Tss=90°C | Thermal steady-state |

## Assumptions & Limitations

- Motor models assume linear magnetics (no saturation)
- EESM uses simplified linear flux model (no lookup tables)
- Semiconductor loss is first-order approximation (no junction temperature feedback)
- Vehicle simulation uses Euler integration, no tire traction model
- All AC quantities assume balanced sinusoidal steady-state unless noted
- SVPWM sector calculation uses symmetric zero-vector splitting

## Future Improvements

- MTPA trajectory calculator (numerical optimization)
- EESM excitation current optimizer
- Thermal network (multi-RC Foster/Cauer)
- Motor parameter identification from step-response
- Control loop phase-margin estimator (Bode plot)
- Battery equivalent circuit (Thevenin, SoC-based)
- CAN/LIN bit-timing calculator
- Resolver angle error and compensation calculator
- Export results to PDF or CSV
