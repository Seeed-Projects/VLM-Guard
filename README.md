# VLM Demo System

This system demonstrates real-time video streaming with dangerous action detection using Vision-Language Models, and RS485 device control.

## Key Features

- **Real-time Video Streaming**: Captures video from camera or video files and streams in real-time
- **Dangerous Action Detection**: Uses vision-language models to analyze video frames and detect dangerous behaviors
- **Intelligent Analysis**: Integrates with vLLM to provide deeper analysis and safety recommendations
- **Web-based Interface**: Displays video stream, analysis results, and vLLM responses in a unified web interface
- **Interactive Chat**: Allows users to interact with vLLM through a chat interface using historical analysis data
- **Analysis History**: Tracks and displays historical analysis results in a database
- **Visual Indicators**: Clear visual indicators for dangerous vs safe actions
- **RS485 Device Support**: Read data from and control RS485 devices (light sensors and light controllers)
- **Automatic Light Control**: Automatically controls RS485 lights based on sensor data and vLLM analysis results
- **Modular Architecture**: Well-structured codebase with clear separation of concerns

## Project Structure

```
vlm_demo/
├── app.py                 # Main application entry point
├── web_ui.py              # Web interface implementation
├── pyproject.toml         # Project dependencies and metadata
├── start_demo.sh          # Startup script
├── README.md              # This file
├── models/                # Model implementations
│   ├── __init__.py        # Package initialization
│   ├── video_streamer.py  # Video streaming and analysis
│   ├── database.py        # Database models and initialization
│   ├── rs485_controller.py     # RS485 controller (integrated light control and sensor reading)
│   ├── rs485_sensor_data_sender.py  # RS485 sensor data sender
│   └── data_visualizer_receiver.py  # Data visualization receiver
├── services/              # Service layer implementations
│   ├── __init__.py        # Package initialization
│   ├── app_service.py     # Application service layer
│   └── config.py          # Configuration management
├── templates/             # Web UI templates
│   └── web_ui.html        # Main web interface
└── data/                  # Data directory (database and images)
    └── vlm_demo.db        # SQLite database for storing analysis records
```

## Prerequisites

1. **Python 3.9+**
2. **Ollama** with required models
3. **Required Python packages** (see pyproject.toml)
4. **Need Jetson or GPU have ARM>8GB**

## Installation

1. Clone or download this repository

```bash
git clone https://github.com/Seeed-Projects/VLM-Guard.git
```

2. Create a virtual environment and activate it:
   
```bash
cd VLM-Guard
pip install uv 
```

3. Install required dependencies:

```bash
uv sync 
source .venv/bin/activate
```

## Model Requirements

The system requires the following models to be available in Ollama:
- `gemma3:4b` - For image analysis and dangerous behavior detection

To install this model:
```bash
# Install Ollama from https://ollama.com/
ollama pull gemma3:4b
ollama serve
```

## Quick Start

### Using the startup script (recommended)
```bash
# Start with default settings
./start_demo.sh

# Or with custom parameters
./start_demo.sh --port 5005 --web-port 5006

# Or using environment variables
PORT=5005 WEB_PORT=5006 ./start_demo.sh

# Without RS485 support
./start_demo.sh --no-rs485

# With video file as source
./start_demo.sh --video-source /path/to/video.mp4

# View all options
./start_demo.sh --help
```

Once started, open your browser and navigate to `http://localhost:5001` to access the web interface.

## Detailed Usage

### Command Line Options

#### start_demo.sh Options
```bash
./start_demo.sh --help

Options:
  --port PORT              UDP端口 (默认: 5000)
  --host HOST              主机地址 (默认: localhost)
  --web-port WEB_PORT      Web界面端口 (默认: 5001)
  --chart-port CHART_PORT  图表数据端口 (默认: 5002)
  --rs485-port RS485_PORT  RS485串口设备 (默认: /dev/ttyTHS1)
  --rs485-baud RS485_BAUD  RS485波特率 (默认: 9600)
  --lux-sensor-addr ADDR   光照传感器地址 (默认: 0x0B)
  --light-control-addr ADDR 灯光控制地址 (默认: 0x01)
  --description-interval SECONDS 分析间隔 (默认: 10)
  --model MODEL            Ollama模型名称 (默认: gemma3:4b)
  --video-source SOURCE    视频源 (默认: 0)
  --vllm-url URL           vLLM API URL (默认: http://localhost:11434/v1/completions)
  --no-rs485               禁用RS485设备支持
  --help                   显示帮助信息
```

Environment variables can also be used for configuration:
- `PORT` - UDP port for data transfer
- `HOST` - Host address
- `WEB_PORT` - Web interface port
- `CHART_PORT` - Chart data port
- `RS485_PORT` - RS485 serial device
- `RS485_BAUD` - RS485 baud rate
- `LUX_SENSOR_ADDR` - Light sensor address
- `LIGHT_CONTROL_ADDR` - Light control device address
- `DESCRIPTION_INTERVAL` - Analysis interval in seconds
- `MODEL` - Ollama model name
- `VIDEO_SOURCE` - Video source
- `VLLM_URL` - vLLM API URL

#### Manual startup
```bash
# Terminal 1: Start the video streamer
python app.py --port 5000 --host localhost

# Terminal 2: Start the web interface
python web_ui.py --port 5000 --host localhost --web-port 5001
```

With direct RS485 device support:
```bash
# Terminal 1: Start the video streamer with direct RS485 support
python app.py --enable-rs485-direct --rs485-port /dev/ttyTHS1 --rs485-baud 9600

# Terminal 2: Start the web interface
python web_ui.py --port 5000 --host localhost --web-port 5001 --chart-port 5002
```

### Web Interface

The web interface consists of three main sections:
1. **Video Stream**: Real-time video display from the camera or video file
2. **Analysis Results**: Current and historical analysis results with danger indicators
3. **vLLM Chat**: Interactive chat interface to communicate with the vLLM model
   - The chat interface automatically includes the latest 20 analysis records as context
   - Users can ask questions about the video analysis history

### Video Source Options

The system supports multiple video sources:
- **Default Camera**: `--video-source 0` (default)
- **Specific Camera**: `--video-source 1` (for second camera)
- **Video File**: `--video-source /path/to/video.mp4`

## System Architecture

### Data Flow

1. **Video Capture**: Video is captured from camera or video file
2. **Frame Analysis**: Every 5 seconds (configurable), a frame is sent to LLaVA model for analysis
3. **Danger Detection**: LLaVA model detects dangerous behaviors and sends results via UDP
4. **vLLM Interaction**: Analysis results are stored in a database for chat context
5. **RS485 Data**: Light sensor readings are processed via Modbus RTU protocol
6. **RS485 Control**: Light control commands are sent via Modbus RTU protocol based on:
   - Sensor data (ambient light levels)
   - vLLM analysis results (danger detection)
7. **Data Display**: All data is displayed in real-time on the web interface
8. **User Interaction**: Users can chat with vLLM through the web interface

### Architecture Layers

The system follows a layered architecture pattern with clear separation of concerns:

1. **Application Layer** (`app.py`): Entry point and main application logic
2. **Service Layer** (`services/`): Business logic and coordination between components
3. **Model Layer** (`models/`): Data models and core functionality implementations
4. **Presentation Layer** (`web_ui.py`, `templates/`): Web interface and user interaction

This architecture improves maintainability, testability, and scalability of the system.

## RS485 Device Control

The system supports RS485 devices including:
1. **Light Sensor**: Reads ambient light levels in Lux
2. **Light Control Device**: Controls RGB lighting via Modbus commands

### Automatic Light Control Logic

When using the `--enable-rs485-direct` option, the system automatically controls the RS485 lights based on two conditions:

1. **Sensor-based Control**:
   - When ambient light level is below 50 Lux, the light turns **red**
   - When ambient light level is 50 Lux or above, the light turns **green**

2. **vLLM Analysis-based Control**:
   - When vLLM detects dangerous behavior, the light turns **yellow**
   - When vLLM determines the scene is safe, the light turns **green**

The vLLM-based control takes precedence over sensor-based control when both conditions are active.

## Ports

- **Port 5000**: UDP data transfer (video frames, analysis results, and vLLM responses)
- **Port 5001**: Web interface for viewing video and analysis
- **Port 5002**: Data visualization

## Troubleshooting

### Common Issues

1. **"无法打开摄像头" (Cannot open camera)**:
   - Ensure you have a camera connected
   - Check camera permissions
   - Try different camera indices (0, 1, 2, etc.)

2. **Connection errors**:
   - Make sure Ollama is running (`ollama serve`)
   - Ensure required models are downloaded (`ollama pull gemma3:4b`)
   - Check that vLLM URL is correct

3. **Web interface doesn't load**:
   - Check that both components are running
   - Verify ports 5000 and 5001 are not blocked by firewall
   - Check browser console for JavaScript errors

4. **RS485 device connection issues**:
   - Check serial port permissions: `ls -l /dev/ttyTHS1`
   - Ensure correct device addresses are configured
   - Verify baud rate settings match your devices

### Debugging Tips

1. **Enable detailed logging**:
   ```bash
   export PYTHON_LOG_LEVEL=DEBUG
   python app.py --port 5000 --host localhost
   ```

2. **Check Ollama status**:
   ```bash
   ollama list  # List installed models
   ollama ps    # Show running models
   ```

3. **Monitor UDP traffic**:
   ```bash
   sudo tcpdump -i lo udp port 5000  # On Linux
   ```

## Performance Optimization

1. **Video Quality**:
   - Adjust JPEG compression quality in `video_streamer.py`
   - Consider using lower resolution for faster processing

2. **Model Performance**:
   - Use GPU acceleration with Ollama if available
   - Consider using smaller models for faster inference

3. **Network Optimization**:
   - Use localhost for minimal latency
   - Ensure sufficient bandwidth for video streaming

4. **RS485 Communication**:
   - Optimize polling intervals for sensor readings
   - Use appropriate baud rates for your hardware

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.com/) for providing the LLM infrastructure
- [LLaVA](https://llava-vl.github.io/) for the vision-language model
- OpenCV for computer vision capabilities
- Flask for web interface framework
- PyModbus for Modbus communication
- SQLAlchemy for database ORM