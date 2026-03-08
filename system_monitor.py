import asyncio
import concurrent.futures
import threading
import time
import os
import psutil
import platform

try:
    import GPUtil
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

def get_cpu_monitor(result_dict, stop_event):
    while not stop_event.is_set():
        result_dict['cpu'] = psutil.cpu_percent(interval=1)
        time.sleep(0.1)

def simulate_heavy_analysis(data):
    start_time = time.time()
    result = sum(i * i for i in range(data))
    duration = time.time() - start_time
    return result, duration

async def monitor_gpu_async(result_dict):
    while True:
        if HAS_GPU:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    result_dict['gpu_load'] = f"{gpu.load * 100:.1f}%"
                    result_dict['gpu_temp'] = f"{gpu.temperature}°C"
                else:
                    result_dict['gpu_load'] = "ไม่พบอุปกรณ์"
                    result_dict['gpu_temp'] = "ไม่พบอุปกรณ์"
            except Exception:
                result_dict['gpu_load'] = "ตรวจหาไม่สำเร็จ"
                result_dict['gpu_temp'] = "ตรวจหาไม่สำเร็จ"
        else:
            result_dict['gpu_load'] = "ไม่พบไดรเวอร์ GPU"
            result_dict['gpu_temp'] = "ไม่พบไดรเวอร์ GPU"
        await asyncio.sleep(2)

async def monitor_system_temps_async(result_dict):
    while True:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    result_dict['cpu_temp'] = f"{entries[0].current}°C"
                    break
            else:
                result_dict['cpu_temp'] = "ระบบไม่รองรับ"
        except Exception:
            result_dict['cpu_temp'] = "ไม่สามารถอ่านค่า"
        await asyncio.sleep(2)

async def main():
    shared_state = {
        'cpu': 0,
        'cpu_temp': 'กำลังอ่าน...',
        'gpu_load': 'กำลังอ่าน...',
        'gpu_temp': 'กำลังอ่าน...'
    }
    
    stop_event = threading.Event()
    cpu_thread = threading.Thread(target=get_cpu_monitor, args=(shared_state, stop_event), daemon=True)
    process_executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    
    print("\n" + "=" * 55)
    print(f"{'ระบบทดสอบประสิทธิภาพ':^55}")
    print("=" * 55)
    
    cpu_thread.start()
    gpu_task = asyncio.create_task(monitor_gpu_async(shared_state))
    temp_task = asyncio.create_task(monitor_system_temps_async(shared_state))
    
    results_log = []
    
    try:
        loop = asyncio.get_running_loop()
        for i in range(1, 6):
            print(f"\n[รอบที่ {i}/5] กำลังเก็บข้อมูล...")
            
            future = loop.run_in_executor(process_executor, simulate_heavy_analysis, 10_000_000)
            await future
            
            current_data = {
                'round': i,
                'cpu': shared_state['cpu'],
                'cpu_temp': shared_state['cpu_temp'],
                'gpu': shared_state['gpu_load'],
                'gpu_temp': shared_state['gpu_temp']
            }
            results_log.append(current_data)
            
            print(f"   > CPU: {current_data['cpu']}% | ความร้อน: {current_data['cpu_temp']}")
            print(f"   > GPU: {current_data['gpu']} | ความร้อน: {current_data['gpu_temp']}")
            await asyncio.sleep(1)
            
        print("\n" + "=" * 70)
        print(f"| {'ครั้งที่':^8} | {'CPU (%)':^10} | {'อุณหภูมิ CPU':^16} | {'การใช้งาน GPU':^18} |")
        print("-" * 70)
        for res in results_log:
            print(f"| {res['round']:^8} | {res['cpu']:^10} | {res['cpu_temp']:^16} | {res['gpu']:^18} |")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nเกิดข้อผิดพลาด: {e}")
    finally:
        stop_event.set()
        process_executor.shutdown(wait=False)
        gpu_task.cancel()
        temp_task.cancel()
        print("\nจบการทำงาน")

if __name__ == "__main__":
    asyncio.run(main())
