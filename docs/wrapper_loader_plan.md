# Wrapper Loader 設計 — 解 EXEPACK 封鎖的 hook 路徑

## 問題

Land.exe / Pe.exe / Space.EXE 三個都被 EXEPACK 壓 + 用 MSC C 5.x overlay (sub-EXE chain in file tail)。直接 hook 必須先 unpack，但 unpack 後 overlay manager 找不到 overlay area (LFA 公式還沒 RE)。

## 解法：Wrapper Loader

**不動原 EXE on disk**。寫個小 DOS `.EXE` 叫 `LE_HOOK.EXE`，做：

1. **Spawn child** = Land.exe (用 INT 21h AH=4B AL=01h 載入不執行)
2. **Locate** child 的 print_func entry 在 memory (= child_image_base_seg : 0x0ECA after reloc)
3. **Patch** 5 bytes `55 8B EC 83 EC` → `EA off_lo off_hi seg_lo seg_hi` (jmp far to our stub)
4. **Stub** 在 LE_HOOK.EXE 自己的 code segment，含 BIOS teletype 印 'H' + 重建 prologue + jmp far 回 child 的 print_func+6
5. **Transfer control** 到 child entry — child 從原始 Land.exe disk file 讀 overlay（沒被動）→ 正常運作

## 關鍵 DOS API: INT 21h AH=4Bh AL=01h

```
入: ES:BX = param block
    DS:DX = ASCIIZ path of child .EXE
    AL = 0x01 (load but don't execute)

Param block layout (for AL=01h):
    +0x00: ENV_SEG (0 = inherit parent)
    +0x02: CMDLINE_PTR (far ptr to command tail)
    +0x06: FCB1_PTR
    +0x0A: FCB2_PTR
    +0x0E: (reserved by DOS for SS value)
    +0x10: SP value (filled by DOS after load)
    +0x12: SS value
    +0x14: IP value
    +0x16: CS value

出: CF set on error, AX = error code
    Or: param block updated with child's CS:IP / SS:SP
```

## Memory Layout 推算

DOS 載入 child：
- Child's PSP at some segment X
- Child's image data starts at (X + 0x10) → ES at child start = X
- Child's image_offset 0xABAA (print_func entry) maps to:
  - physical address = X*16 + 0x100 + 0xABAA = X*16 + 0xACAA
  - or seg:off = X:(0xACAA)

要從 wrapper patch child：
- 我們知道 child's CS (from param block +0x16)
- 該值 = X + 0x10 + 0x0526 (relocated, since image relative cs was 0x0526)
- 反算 child_image_base_seg = X + 0x10 = CS_from_param - 0x526

**但**：4B01h spec 沒明確說 PSP seg 怎麼拿。要實測。Possible workarounds:
1. 假設 DS=PSP_seg, 從 child startup 邏輯逆推
2. 用 INT 21h AH=62h (get current PSP) — 但這給 parent's，不是 child's
3. 改用 INT 21h AH=4B AL=03h (Load Overlay) — 給 explicit load address

## Stub 程式碼 (NASM)

```asm
; LE_HOOK.EXE — wrapper loader for Land.exe
BITS 16
CPU 8086

org 0x100   ; .COM format (simpler than .EXE)
            ; or use .EXE format for >64K code

start:
    mov ax, cs
    mov ds, ax
    mov es, ax

    ; ---- Shrink our memory allocation so child has room ----
    mov ah, 0x4A          ; resize memory block
    mov bx, 0x1000        ; keep 64KB (sufficient for wrapper)
    int 0x21

    ; ---- INT 21h AH=4B AL=01: load child not execute ----
    mov ax, 0x4B01
    mov dx, child_path    ; DS:DX = "Land.exe\0"
    mov bx, param_block   ; ES:BX = param block
    int 0x21
    jc  load_error

    ; ---- Compute child's image base segment ----
    ; CS_after_reloc = PSP_seg + 0x10 + 0x526   (image-rel CS was 0x526)
    ; => PSP_seg = CS - 0x536
    mov ax, [param_block + 0x16]    ; child CS
    sub ax, 0x536                    ; PSP_seg
    add ax, 0x10                     ; image base seg = PSP_seg + 0x10
    mov [child_img_base_seg], ax

    ; ---- Patch print_func entry: image_offset 0xABAA ----
    mov es, ax                       ; ES = child image base
    mov di, 0xABAA
    mov byte [es:di],   0xEA         ; JMP FAR opcode
    mov word [es:di+1], 0x0000       ; offset = 0x0000
    mov ax, cs                       ; stub is in OUR cs
    add ax, hook_stub_seg_offset     ; if stub is at known offset from cs
    mov [es:di+3], ax                ; segment

    ; ---- Transfer control to child ----
    mov ax, [param_block + 0x10]
    mov bx, [param_block + 0x12]
    mov cx, [param_block + 0x14]
    mov dx, [param_block + 0x16]
    cli
    mov ss, bx                       ; child SS
    mov sp, ax                       ; child SP
    sti
    push dx                          ; child CS
    push cx                          ; child IP
    retf                             ; transfer

load_error:
    mov ah, 0x09
    mov dx, err_msg
    int 0x21
    mov ax, 0x4C01
    int 0x21

; ---- Our hook stub: called when child does `call far 09CE:0ECA` ----
; (Same as previous hook_stub.bin, but PFSEG must be RELOCATED segment, not image-rel)
hook_stub:
    push ax
    push bx
    mov ah, 0x0E
    mov al, 'H'
    mov bh, 0
    mov bl, 7
    int 0x10
    pop bx
    pop ax
    push bp
    mov bp, sp
    sub sp, 0x0E
    ; jmp far to child print_func + 6
    ; SEG = child_img_base_seg + 0x9CE  (computed at runtime, can't be in opcode!)
    ; ... this needs runtime fixup or alternative approach
    jmp far [pf_target]      ; indirect jump via memory pointer
pf_target:
    dw 0x0ED0       ; offset
    dw 0            ; segment (filled at runtime)

; ---- Data ----
child_path: db "Land.exe", 0
err_msg:    db "ERROR loading Land.exe$"
param_block:
    dw 0            ; env seg (inherit)
    dd 0            ; cmd line ptr
    dd 0            ; fcb1
    dd 0            ; fcb2
    dd 0            ; ss:sp (filled by DOS)
    dd 0            ; cs:ip (filled by DOS)
child_img_base_seg: dw 0
```

## 雷區

1. **PSP segment 反推可能不準** — 不同 EXEPACK + relocator 行為不同。可能要 dynamic test
2. **Overlay manager 從 env block 拿 EXE path** — 如果 child 沒有自己的 env，會用 parent 的，path 指向 LE_HOOK.EXE → 開錯檔
   - 對策：在 param block 設 env_seg = own env，或用 4B03 Load Overlay 模式繞過
3. **CS:IP 在 stub 內必須能 jmp 回 child code** — 但 child 的 segment 是 runtime relocated，不能 hardcode in stub。用 indirect far jmp `jmp far [memory]` 並 fill 該 memory at patch time
4. **Stub 自己的 segment** — 必須是 child memory 內可達。如果 stub 在 wrapper 的 code segment，wrapper exit 前 stub 跟著消失 ❌
   - 對策：把 stub 拷到 conventional memory 某固定區（child 不會用到的地方），patch 時指向那
   - 或更乾淨：用 INT 21h AH=48h alloc 一塊 paragraph，把 stub 寫進去，patch 用那 segment

## 進度

當前狀態：**設計階段**。
下次 session 起點：
1. 寫 minimal version 只 spawn child (4B01h → 4B00h 用 same exec)，verify wrapper 跟 child 都能跑
2. 加 patch 一個 byte (e.g., 修改 child's `mov ax, 0x190F` → `mov ax, 0x190E`) 確認 memory patch 機制可行
3. 加 stub allocation + 5-byte hook + transfer
4. ✅ 終於看到 'H'
