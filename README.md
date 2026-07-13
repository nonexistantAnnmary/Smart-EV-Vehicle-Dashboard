A modular Python application that simulates an electric vehicle, displays real-time telemetry through an interactive dashboard, logs operational data, visualizes energy consumption, and predicts the remaining driving range using machine learning.

## Features

- Real-time EV telemetry simulation
- Battery SOC and SOH monitoring
- Live speed and motor temperature display
- Multiple driving modes (Eco, Normal, Sport)
- Charging simulation
- Fault detection simulation
- Live energy consumption graph
- CSV telemetry logging
- Machine Learning-based range prediction
- Clean modular architecture

## Technologies

- Python
- CustomTkinter
- Matplotlib
- Pandas
- NumPy
- Scikit-learn

## Project Structure

vehicle.py        → EV simulation engine  
dashboard.py      → User interface  
graph.py          → Live telemetry visualization  
logger.py         → CSV telemetry logging  
prediction.py     → ML range prediction  
utils.py          → Helper functions  
app.py            → Main application

## Future Improvements

- CAN Bus integration
- Battery Digital Twin
- GPS route prediction
- Cloud telemetry
- Advanced battery health analytics
