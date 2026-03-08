import asyncio
import concurrent.futures
import threading
import time
import os
import psutil
import platform

# ฟังก์ชันสำหรับ Thread: ใช้ตรวจสอบ CPU เปอร์เซ็นต์ (เนื่องจากเป็น Blocking call)
def get_cpu_monitor(result_dict, stop_event):
    while not stop_event.is_set():
        # psutil.cpu_percent(interval=1) จะค้างไว้ 1 วินาทีเพื่อหาค่าเฉลี่ย
        result_dict['cpu'] = psutil.cpu_percent(interval=1)
        time.sleep(0.1)

# ฟังก์ชันสำหรับ Process Pool: จำลองงานคำนวณที่ใช้ CPU หนัก (CPU-bound)
def simulate_heavy_analysis(data):
    start_time = time.time()
    # คำนวณเลขจำนวนมาก
    result = sum(i * i for i in range(data))
    duration = time.time() - start_time
    return result, duration

# ฟังก์ชัน Async: จัดการ Event Loop และแสดงผล
async def main():
    shared_state = {'cpu': 0}
    stop_event = threading.Event()
    
    # 1. Thread: รันตัว Monitor CPU ไว้เบื้องหลัง
    cpu_thread = threading.Thread(
        target=get_cpu_monitor, 
        args=(shared_state, stop_event), 
        daemon=True
    )
    
    # 2. Process Pool: เตรียมตัวรันงานคำนวณหนักขนานไปกับตัว Monitor
    process_executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    
    print("\n" + "=" * 50)
    print(f"{'ระบบตรวจสอบประสิทธิภาพ CPU':^50}")
    print(f"{'OS: ' + platform.system() + ' | PID: ' + str(os.getpid()):^50}")
    print("=" * 50)
    
    cpu_thread.start()
    results_log = []
    
    try:
        loop = asyncio.get_running_loop()
        for i in range(1, 6):
            print(f"\n[รอบที่ {i}/5] กำลังเก็บข้อมูลพร้อมจำลองการคำนวณ...")
            
            # 3. Async Task: ส่งงานหนักไปทำใน Process Pool โดยไม่บล็อก Main Loop
            future = loop.run_in_executor(process_executor, simulate_heavy_analysis, 10_000_000)
            await future # รอให้งานในรอบนั้นเสร็จ
            
            current_cpu = shared_state['cpu']
            results_log.append({'round': i, 'cpu': current_cpu})
            
            print(f"   > บันทึกค่าการใช้งาน CPU: {current_cpu}%")
            await asyncio.sleep(1)
            
        # แสดงตารางสรุป
        print("\n" + "=" * 40)
        print(f"| {'รอบที่':^10} | {'การใช้งาน CPU (%)':^20} |")
        print("-" * 40)
        for res in results_log:
            print(f"| {res['round']:^10} | {res['cpu']:^20} |")
        print("=" * 40)
        
    except Exception as e:
        print(f"\nเกิดข้อผิดพลาด: {e}")
    finally:
        stop_event.set()
        process_executor.shutdown(wait=False)
        print("\nจบการทำงาน")

if __name__ == "__main__":
    asyncio.run(main())
