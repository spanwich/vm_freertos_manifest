# FreeRTOS QEMU MPS2-AN385 Emulation Setup Guide

## Overview

This document provides step-by-step instructions to reproduce a working FreeRTOS emulation on QEMU MPS2-AN385 with proper console output, starting from a freshly cloned FreeRTOS GitHub repository.

## Prerequisites

### Required Tools
```bash
# ARM cross-compilation toolchain
sudo apt-get install gcc-arm-none-eabi

# QEMU ARM system emulation
sudo apt-get install qemu-system-arm

# Build tools
sudo apt-get install build-essential make cmake
```

### Verify Installation
```bash
arm-none-eabi-gcc --version
qemu-system-arm --version
```

## Step 1: Clone FreeRTOS Repository

```bash
cd /home/user/projects  # Replace with your preferred directory
git clone --recursive https://github.com/FreeRTOS/FreeRTOS.git
cd FreeRTOS
git submodule update --init FreeRTOS/Source
```

## Step 2: Navigate to MPS2-AN385 Demo Directory

```bash
cd FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/build/gcc
```

## Step 3: Create Simplified Build Configuration

### Create `Makefile_simple`

```makefile
# Simplified Makefile for FreeRTOS MPS2-AN385 QEMU Demo
# Removes trace recorder dependencies and complex demo components

CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# Compiler flags
CFLAGS = -mthumb -mcpu=cortex-m3 -ffreestanding -g3 -Os
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -Wall -Wextra -Wshadow -Wno-unused-value
CFLAGS += -MMD -MP

# Include paths
INCLUDE_PATHS = -I./../../../../Source/include
INCLUDE_PATHS += -I./../../../../Source/portable/GCC/ARM_CM3
INCLUDE_PATHS += -I./../../../../Demo/CORTEX_MPS2_QEMU_IAR_GCC
INCLUDE_PATHS += -I./../../../../Demo/CORTEX_MPS2_QEMU_IAR_GCC/CMSIS

# Preprocessor defines
DEFINES = -DconfigINCLUDE_FREERTOS_TASK_H=0
DEFINES += -include ./../../../../Demo/CORTEX_MPS2_QEMU_IAR_GCC/FreeRTOSConfig_blinky.h

# FreeRTOS kernel source files
KERNEL_DIR = ./../../../../Source
SOURCE_FILES = $(KERNEL_DIR)/tasks.c
SOURCE_FILES += $(KERNEL_DIR)/list.c
SOURCE_FILES += $(KERNEL_DIR)/queue.c
SOURCE_FILES += $(KERNEL_DIR)/timers.c
SOURCE_FILES += $(KERNEL_DIR)/event_groups.c
SOURCE_FILES += $(KERNEL_DIR)/stream_buffer.c

# Memory management
SOURCE_FILES += $(KERNEL_DIR)/portable/MemMang/heap_4.c

# ARM Cortex-M3 port
SOURCE_FILES += $(KERNEL_DIR)/portable/GCC/ARM_CM3/port.c

# Demo application files
SOURCE_FILES += main_simple.c
SOURCE_FILES += startup_gcc.c
SOURCE_FILES += RegTest.c
SOURCE_FILES += printf-stdarg.c
SOURCE_FILES += assert.c

# Object files
OBJS = $(SOURCE_FILES:.c=.o)
OBJS := $(addprefix output/,$(notdir $(OBJS)))

# Dependency files
DEPS = $(OBJS:.o=.d)

# Linker flags
LDFLAGS = -T ./mps2_m3.ld -Xlinker -Map=./output/RTOSDemo.map
LDFLAGS += -Xlinker --gc-sections -nostartfiles
LDFLAGS += -specs=nano.specs -specs=rdimon.specs

# Default target
all: output/RTOSDemo.out size

# Create output directory
output:
	mkdir -p output

# Compile rule for all source files
define compile-rule
output/$(notdir $(1:.c=.o)): $(1) | output
	$(CC) $(CFLAGS) $(INCLUDE_PATHS) $(DEFINES) -MF"output/$(notdir $(1:.c=.d))" -MT output/$(notdir $(1:.c=.o)) -c $(1) -o output/$(notdir $(1:.c=.o))
endef

$(foreach src,$(SOURCE_FILES),$(eval $(call compile-rule,$(src))))

# Link
output/RTOSDemo.out: $(OBJS)
	@echo
	@echo "--- Final linking ---"
	@echo
	$(CC) $(CFLAGS) $(INCLUDE_PATHS) $(DEFINES) $(LDFLAGS) $(OBJS) -o $@

# Size information
size: output/RTOSDemo.out
	$(SIZE) output/RTOSDemo.out

# Clean
clean:
	rm -f ./output/RTOSDemo.out ./output/RTOSDemo.map ./output/*.o ./output/*.d

.PHONY: all clean size

# Include dependency files
-include $(DEPS)
```

### Create `FreeRTOSConfig_blinky.h`

```c
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

/* Disable trace recorder to simplify build */
#define configUSE_TRACE_FACILITY                0
#define configUSE_STATS_FORMATTING_FUNCTIONS    0

/* Basic FreeRTOS configuration for MPS2-AN385 */
#define configUSE_PREEMPTION                    1
#define configUSE_IDLE_HOOK                     1
#define configUSE_TICK_HOOK                     1
#define configCPU_CLOCK_HZ                      ( ( unsigned long ) 25000000 )
#define configTICK_RATE_HZ                      ( ( TickType_t ) 1000 )
#define configMAX_PRIORITIES                    ( 7 )
#define configMINIMAL_STACK_SIZE                ( ( unsigned short ) 512 )
#define configTOTAL_HEAP_SIZE                   ( ( size_t ) ( 100 * 1024 ) )
#define configMAX_TASK_NAME_LEN                 ( 10 )
#define configUSE_16_BIT_TICKS                  0
#define configIDLE_SHOULD_YIELD                 1
#define configUSE_MUTEXES                       1
#define configQUEUE_REGISTRY_SIZE               8
#define configCHECK_FOR_STACK_OVERFLOW          2
#define configUSE_RECURSIVE_MUTEXES             1
#define configUSE_MALLOC_FAILED_HOOK            1
#define configUSE_APPLICATION_TASK_TAG          0
#define configUSE_COUNTING_SEMAPHORES           1
#define configGENERATE_RUN_TIME_STATS           0

/* Co-routine definitions */
#define configUSE_CO_ROUTINES                   0
#define configMAX_CO_ROUTINE_PRIORITIES         ( 2 )

/* Software timer definitions */
#define configUSE_TIMERS                        1
#define configTIMER_TASK_PRIORITY               ( 2 )
#define configTIMER_QUEUE_LENGTH                10
#define configTIMER_TASK_STACK_DEPTH            ( configMINIMAL_STACK_SIZE * 2 )

/* Set the following definitions to 1 to include the API function, or zero to exclude the API function. */
#define INCLUDE_vTaskPrioritySet                1
#define INCLUDE_uxTaskPriorityGet               1
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskCleanUpResources           1
#define INCLUDE_vTaskSuspend                    1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelay                      1

/* Cortex-M specific definitions */
#ifdef __NVIC_PRIO_BITS
    #define configPRIO_BITS         __NVIC_PRIO_BITS
#else
    #define configPRIO_BITS         4        /* 15 priority levels */
#endif

/* Lowest interrupt priority that can be used by the kernel */
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY   15
/* Highest interrupt priority that can be used by API functions */
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5
/* Define to map interrupt priority values */
#define configKERNEL_INTERRUPT_PRIORITY ( configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS) )
#define configMAX_SYSCALL_INTERRUPT_PRIORITY ( configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS) )

/* Definitions that map the FreeRTOS port interrupt handlers to their CMSIS standard names */
#define vPortSVCHandler SVC_Handler
#define xPortPendSVHandler PendSV_Handler
#define xPortSysTickHandler SysTick_Handler

/* Disable static allocation to avoid linking errors */
#define configSUPPORT_STATIC_ALLOCATION         0
#define configSUPPORT_DYNAMIC_ALLOCATION        1

#endif /* FREERTOS_CONFIG_H */
```

## Step 4: Create Demo Application with UART Support

### Create `main_simple.c`

```c
/* Simple FreeRTOS demo with proper CMSDK UART initialization for MPS2-AN385 */

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "timers.h"
#include <stdio.h>

/* CMSDK UART for MPS2-AN385 - proper initialization */
#define UART0_BASE 0x40004000
#define UART_DR    (*(volatile unsigned int *)(UART0_BASE + 0x000))  // Data Register
#define UART_STATE (*(volatile unsigned int *)(UART0_BASE + 0x004))  // State Register
#define UART_CTRL  (*(volatile unsigned int *)(UART0_BASE + 0x008))  // Control Register
#define UART_INTSTATUS (*(volatile unsigned int *)(UART0_BASE + 0x00C))  // Interrupt Status
#define UART_BAUDDIV (*(volatile unsigned int *)(UART0_BASE + 0x010))  // Baud Divisor

/* UART Control Register bits */
#define UART_CTRL_TX_EN     (1 << 0)  // Transmitter enable
#define UART_CTRL_RX_EN     (1 << 1)  // Receiver enable
#define UART_CTRL_TX_INT_EN (1 << 2)  // TX interrupt enable
#define UART_CTRL_RX_INT_EN (1 << 3)  // RX interrupt enable

/* UART State Register bits */
#define UART_STATE_TX_FULL  (1 << 0)  // Transmitter full
#define UART_STATE_RX_FULL  (1 << 1)  // Receiver full

void uart_init(void) {
    /* Configure UART for basic operation */
    UART_BAUDDIV = 16;  // Set baud rate (25MHz / 16 = ~1.5625M, but QEMU is flexible)
    UART_CTRL = UART_CTRL_TX_EN | UART_CTRL_RX_EN;  // Enable TX and RX
}

void uart_putc(char c) {
    /* Wait until transmitter is not full */
    while (UART_STATE & UART_STATE_TX_FULL) {
        /* Wait */
    }
    
    /* Write character */
    UART_DR = c;
}

void uart_puts(const char* str) {
    while (*str) {
        uart_putc(*str++);
    }
}

/* Task priorities */
#define mainQUEUE_RECEIVE_TASK_PRIORITY    ( tskIDLE_PRIORITY + 2 )
#define mainQUEUE_SEND_TASK_PRIORITY       ( tskIDLE_PRIORITY + 1 )

/* The rate at which data is sent to the queue */
#define mainTASK_SEND_FREQUENCY_MS         pdMS_TO_TICKS( 200UL )
#define mainTIMER_SEND_FREQUENCY_MS        pdMS_TO_TICKS( 2000UL )

/* Queue length */
#define mainQUEUE_LENGTH                   ( 2 )

/* Values sent to the queue */
#define mainVALUE_SENT_FROM_TASK           ( 100UL )
#define mainVALUE_SENT_FROM_TIMER          ( 200UL )

/* Function prototypes */
static void prvQueueReceiveTask( void *pvParameters );
static void prvQueueSendTask( void *pvParameters );
static void prvQueueSendTimerCallback( TimerHandle_t xTimerHandle );

/* The queue used by both tasks */
static QueueHandle_t xQueue = NULL;

int main( void )
{
    TimerHandle_t xTimer = NULL;

    /* Initialize UART first */
    uart_init();
    
    /* Test UART output */
    uart_puts("=== FreeRTOS MPS2-AN385 Demo Starting ===\r\n");
    uart_puts("UART initialized and working!\r\n");
    uart_puts("Creating queue and tasks...\r\n");

    /* Create the queue */
    xQueue = xQueueCreate( mainQUEUE_LENGTH, sizeof( uint32_t ) );

    if( xQueue != NULL )
    {
        uart_puts("Queue created successfully!\r\n");
        
        /* Start the two tasks */
        uart_puts("Creating tasks...\r\n");
        xTaskCreate( prvQueueReceiveTask,           /* Function that implements the task */
                     "Rx",                          /* Text name for the task */
                     configMINIMAL_STACK_SIZE,      /* Stack size in words, not bytes */
                     NULL,                          /* Parameter passed into the task */
                     mainQUEUE_RECEIVE_TASK_PRIORITY,/* Priority at which the task is created */
                     NULL );                        /* Used to pass out the created task's handle */

        xTaskCreate( prvQueueSendTask, "TX", configMINIMAL_STACK_SIZE, NULL, mainQUEUE_SEND_TASK_PRIORITY, NULL );
        uart_puts("Tasks created successfully!\r\n");

        /* Create the software timer */
        xTimer = xTimerCreate( "Timer",                     /* A text name, purely to help debugging */
                               mainTIMER_SEND_FREQUENCY_MS, /* The timer period, in this case 2000ms */
                               pdTRUE,                      /* This is an auto-reload timer */
                               NULL,                        /* The ID is not used, so can be set to anything */
                               prvQueueSendTimerCallback    /* The callback function that is executed when the timer expires */
                               );

        if( xTimer != NULL )
        {
            uart_puts("Timer created successfully!\r\n");
            xTimerStart( xTimer, 0 );
            uart_puts("Timer started!\r\n");
        }

        /* Start the tasks and timer running */
        uart_puts("Starting FreeRTOS scheduler...\r\n");
        vTaskStartScheduler();
    }

    /* If all is well, the scheduler will now be running, and the following
     * line will never be reached. If the following line does execute, then
     * there was insufficient FreeRTOS heap memory available for the Idle and/or
     * timer tasks to be created. See the memory management section on the
     * FreeRTOS web site for more details on the FreeRTOS heap
     * http://www.freertos.org/a00111.html. */
    for( ; ; );
}

static void prvQueueSendTask( void *pvParameters )
{
    TickType_t xNextWakeTime;
    const uint32_t ulValueToSend = mainVALUE_SENT_FROM_TASK;

    /* Remove compiler warning about unused parameter */
    ( void ) pvParameters;

    uart_puts("[TX Task] Task started!\r\n");

    /* Initialise xNextWakeTime - this only needs to be done once */
    xNextWakeTime = xTaskGetTickCount();

    for( ; ; )
    {
        /* Place this task in the blocked state until it is time to run again */
        vTaskDelayUntil( &xNextWakeTime, mainTASK_SEND_FREQUENCY_MS );

        /* Send to the queue - causing the queue receive task to unblock and
         * write to the console. 0 is used as the block time so the sending
         * operation will not block - it shouldn't need to block as the queue
         * should always be empty at this point in the code */
        uart_puts("[TX Task] Sending message\r\n");
        xQueueSend( xQueue, &ulValueToSend, 0U );
    }
}

static void prvQueueSendTimerCallback( TimerHandle_t xTimerHandle )
{
    const uint32_t ulValueToSend = mainVALUE_SENT_FROM_TIMER;

    /* This is the software timer callback function. The software timer has a
     * period of two seconds and is reset each time a key is pressed. This
     * callback function will execute if the timer expires, which will only happen
     * if a key is not pressed for two seconds */

    /* Avoid compiler warnings resulting from the unused parameter */
    ( void ) xTimerHandle;

    /* Send to the queue - causing the queue receive task to unblock and
     * write out a message. This function is called from the timer/daemon task, so
     * must not block. Hence the block time is set to 0 */
    uart_puts("[Timer] Sending timer message\r\n");
    xQueueSend( xQueue, &ulValueToSend, 0U );
}

static void prvQueueReceiveTask( void *pvParameters )
{
    uint32_t ulReceivedValue;
    const uint32_t ulExpectedValue = mainVALUE_SENT_FROM_TASK;

    /* Remove compiler warning about unused parameter */
    ( void ) pvParameters;

    uart_puts("[RX Task] Task started! Waiting for messages...\r\n");

    for( ; ; )
    {
        /* Wait until something arrives in the queue - this task will block
         * indefinitely provided INCLUDE_vTaskSuspend is set to 1 in
         * FreeRTOSConfig.h */
        xQueueReceive( xQueue, &ulReceivedValue, portMAX_DELAY );

        /* To get here something must have been received from the queue, but
         * is it the expected value? If it is, write the message to the
         * console before looping back to block on the queue again */
        if( ulReceivedValue == ulExpectedValue )
        {
            /* This message was sent from the task */
            uart_puts("[RX Task] Message received from TASK\r\n");
        }
        else
        {
            /* This message was sent from the timer */
            uart_puts("[RX Task] Message received from TIMER\r\n");
        }
    }
}

/* Hook functions */
void vApplicationMallocFailedHook( void )
{
    /* Called if a call to pvPortMalloc() fails because there is insufficient
     * free memory available in the FreeRTOS heap. pvPortMalloc() is called
     * internally by FreeRTOS API functions that create tasks, queues, software
     * timers, and semaphores. The size of the FreeRTOS heap is set by the
     * configTOTAL_HEAP_SIZE configuration constant in FreeRTOSConfig.h */
    taskDISABLE_INTERRUPTS();
    for( ; ; );
}

void vApplicationStackOverflowHook( TaskHandle_t pxTask, char *pcTaskName )
{
    ( void ) pcTaskName;
    ( void ) pxTask;

    /* Run time stack overflow checking is performed if
     * configCHECK_FOR_STACK_OVERFLOW is defined to 1 or 2. This hook
     * function is called if a stack overflow is detected */
    taskDISABLE_INTERRUPTS();
    for( ; ; );
}

void vApplicationIdleHook( void )
{
    /* This is just a trivial example of an idle hook. It is called on each
     * cycle of the idle task. It must *NOT* attempt to block. In this case the
     * idle task just sleeps to lower the CPU usage */
}

void vApplicationTickHook( void )
{
    /* The tick hook is called every tick */
}

/* Dummy timer handlers */
void TIMER0_Handler( void ) 
{
    /* Timer 0 interrupt handler */
}

void TIMER1_Handler( void ) 
{
    /* Timer 1 interrupt handler */
}
```

### Create `assert.c`

```c
#include "FreeRTOS.h"

void vAssertCalled(const char *pcFileName, uint32_t ulLine) {
    (void)pcFileName;
    (void)ulLine;
    taskDISABLE_INTERRUPTS();
    for(;;);
}
```

## Step 5: Build and Run

### Build the Demo

```bash
cd /path/to/FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/build/gcc
make -f Makefile_simple clean
make -f Makefile_simple
```

Expected output:
```
   text	   data	    bss	    dec	    hex	filename
  13498	    228	 104489	 118215	  1cdc7	./output/RTOSDemo.out
```

### Run the Emulation

```bash
qemu-system-arm -machine mps2-an385 -kernel ./output/RTOSDemo.out -serial stdio -monitor none -nographic
```

## Expected Output

```
=== FreeRTOS MPS2-AN385 Demo Starting ===
UART initialized and working!
Creating queue and tasks...
Queue created successfully!
Creating tasks...
Tasks created successfully!
Timer created successfully!
Timer started!
Starting FreeRTOS scheduler...
[RX Task] Task started! Waiting for messages...
[TX Task] Task started!
[TX Task] Sending message
[RX Task] Message received from TASK
[TX Task] Sending message
[RX Task] Message received from TASK
[Timer] Sending timer message
[RX Task] Message received from TIMER
...
```

## Key Changes from Original Repository

1. **Simplified Build System**: Removed trace recorder dependencies
2. **Custom FreeRTOS Configuration**: Disabled complex features, focused on basic multitasking
3. **Proper UART Initialization**: Added CMSDK UART setup for MPS2-AN385
4. **Fixed QEMU Command**: Used `-serial stdio -monitor none` to resolve character device conflicts
5. **Custom Demo Application**: Created focused queue/timer demonstration

## Troubleshooting

### No Output
- Verify QEMU command uses `-serial stdio -monitor none`
- Ensure UART initialization is called first in main()
- Check ARM toolchain is properly installed

### Build Errors
- Ensure all source files are created in correct locations
- Verify FreeRTOS submodules are initialized
- Check compiler flags match Cortex-M3 requirements

### QEMU Errors
- Verify `qemu-system-arm` supports `mps2-an385` machine
- Ensure kernel file path is correct
- Check ELF file is properly generated