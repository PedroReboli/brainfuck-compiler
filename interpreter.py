from __future__ import annotations
import enum
import sys
from enum import Enum
from typing import NamedTuple, Optional
import llvmlite.ir as ll
import llvmlite.binding as llvm
class Token(Enum):
    INCREMENT = 0
    DECREMENT = 1
    MOVE_LEFT = 2
    MOVE_RIGHT = 3
    STDOUT = 4
    STDINT = 5
    LOOP_OPEN = 6
    LOOP_CLOSE = 7
OPTMIZABLE= (Token.INCREMENT, Token.DECREMENT, Token.MOVE_LEFT, Token.MOVE_RIGHT)
class Instruction:
    def __init__(self, token_type:Token,index:int, optional:Optional[Instruction] = None) -> None:
        self.token_type = token_type
        self._optional = optional
        self.index = index
        self.times: int = 1
        pass
    # getter
    @property
    def optional(self):
        assert self._optional
        return self._optional
    @optional.setter
    def optional(self,value:Instruction):
        assert value
        self._optional = value
    def __repr__(self) -> str:
        return str(self.token_type) 
        pass
        

class WhileBlock(NamedTuple):
    cond:ll.Block
    body:ll.Block
    end:ll.Block

def bytecode_to_assembly(code:list[Instruction]) -> str:
    asm_code = """
section     .text
global      _start
_start:
MOV qword [RSP], 0
MOV r10, 0
"""
    
    for c in code:
        match c.token_type:
            case Token.MOVE_RIGHT: # B R A N C H L E S S - A S S E M B L Y
                asm_code+=("ADD r10, 4" + "\n"
                "MOV r11, RBP"+ "\n"
                "MOV  r9, 4"+ "\n"
                "MOV  r8, 0"+ "\n"
                "LEA RAX, [RBP+RSP]"+ "\n"
                "CMPXCHG [r10+RSP], r8"+ "\n"
                "CMP r10, r11"+ "\n" #r10 >= r11
                "CMOVAE r8, r9"+ "\n"
                "MOV r9, 0"+ "\n"
                "CMOVB r9, [r10+RSP]"+ "\n"
                "MOV [r10+RSP], r9"+ "\n"
                "ADD RBP, r8" + "\n")
            case Token.MOVE_LEFT:
                asm_code+="SUB r10, 4" + "\n"
            case Token.INCREMENT:
                asm_code+="ADD BYTE  [RSP+r10], 1" + "\n"
            case Token.DECREMENT:
                asm_code+="DEC BYTE  [RSP+r10]" + "\n"
            case Token.STDOUT:
                asm_code += ("MOV EAX, 1 \n"\
                "MOV EDI, 1 \n"\
                "LEA RSI, [RSP+r10] \n"\
                "MOV EDX, 1 \n"\
                "SYSCALL \n")
            case Token.STDINT:
                print("Not Implemented")
                raise ValueError("Not Implemented")
            case Token.LOOP_OPEN:
                asm_code += (f"_tagN{c.index}s: \n"
                "MOV EBX, [RSP+r10] \n"
                "CMP EBX, 0 \n"
                f"JE _tagN{c.optional.index}s \n")

            case Token.LOOP_CLOSE:
                asm_code += (f"_tagN{c.index}s: \n"
                "MOV EBX, [RSP+r10] \n"
                "CMP EBX, 0 \n"
                f"JNE _tagN{c.optional.index}s \n")

    asm_code += "MOV EAX, 1 \n"
    asm_code += "INT 0x80 \n"
    return asm_code

def bytecode_optimized_to_assembly(code:list[Instruction]): #wip
    file = """
section     .text
global      _start
_start:
MOV qword [RSP], 0
MOV r10, 0
"""
    
    for c in code:
        match c.token_type:
            case Token.MOVE_RIGHT: # something breaking here
                file+=(f"ADD r10, {4 * c.times}" + "\n"
                "MOV r11, RBP"+ "\n"
                f"MOV  r9, {4 * c.times}"+ "\n"
                "MOV  r8, 0"+ "\n"
                "LEA RAX, [RBP+RSP]"+ "\n"
                "CMPXCHG [r10+RSP], r8"+ "\n"
                "CMP r10, r11"+ "\n"
                "CMOVAE r8, r9"+ "\n"
                "MOV r9, 0"+ "\n"
                "CMOVB r9, [r10+RSP]"+ "\n"
                "MOV [r10+RSP], r9"+ "\n"
                "ADD RBP, r8" + "\n")
            case Token.MOVE_LEFT:
                file+=f"SUB r10, {4 * c.times}" + "\n"
            case Token.INCREMENT:
                file+=f"ADD WORD [RSP+r10], {c.times}" + "\n"
            case Token.DECREMENT:
                file+=f"SUB WORD [RSP+r10], {c.times}" + "\n"
            case Token.STDOUT:
                file += ("MOV EAX, 1 \n"\
                "MOV EDI, 1 \n"\
                "LEA RSI, [RSP+r10] \n"\
                "MOV EDX, 1 \n"\
                "SYSCALL \n")
            case Token.STDINT:
                print("Not implement")
                raise ValueError("Not implement")
            case Token.LOOP_OPEN:
                file += (f"_tagN{c.index}s: \n"
                "MOV EBX, [RSP+r10] \n"
                "CMP EBX, 0 \n"
                f"JE _tagN{c.optional.index}s \n")

            case Token.LOOP_CLOSE:
                file += (f"_tagN{c.index}s: \n"
                "MOV EBX, [RSP+r10] \n"
                "CMP EBX, 0 \n"
                f"JNE _tagN{c.optional.index}s \n")

    file += "MOV EAX, 1 \n"
    file += "INT 0x80 \n"
    open("test.asm","w").write(file)

def bytecode_to_llvm(code:list[Instruction]): #WIP
    # WhileBlock = namedtuple('WhileBlock', ["cond_block","body_block","end_block"])
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    builder = ll.IRBuilder()
    mod = ll.Module()
    fnty = ll.FunctionType(ll.VoidType(),(ll.VoidType(),))
    entry = ll.Function(mod,fnty,"entry")
    bb_entry = entry.append_basic_block()
    loops_blocks:list[WhileBlock] = []
    builder.position_at_end(bb_entry)
    stack_base = builder.alloca(ll.IntType(32),None,'')
    builder.store_reg(ll.Constant(ll.IntType(32),0),ll.IntType(32),"r10","pointer")
    builder.store_reg(ll.Constant(ll.IntType(32),0),ll.IntType(32),"r12","mem_size")
    putchar_fnty = ll.FunctionType(ll.IntType(32),(ll.IntType(32),))
    putchar = ll.Function(mod,putchar_fnty,"putchar")
    # builder.position_at_end(bb_entry)
    for c in code:
        match c.token_type:
            case Token.MOVE_RIGHT:
                end = entry.append_basic_block()

                add_memory_block  = entry.append_basic_block()
                builder.position_at_end(add_memory_block)
                pointer = builder.load_reg(ll.IntType(32),"r10")
                builder.add(pointer,ll.Constant(ll.IntType(32),4))
                builder.store_reg(pointer, ll.IntType(32), "r10")
                builder.alloca(ll.IntType(32))
                mem_size = builder.load_reg(ll.IntType(32), "r12")
                builder.add(mem_size,ll.Constant(ll.IntType(32),4))
                builder.store_reg(pointer, ll.IntType(32), "r12")
                builder.branch(end)
                no_add_memory_block = entry.append_basic_block()
                builder.position_at_end(no_add_memory_block)
                builder.add(pointer,ll.Constant(ll.IntType(32),4))
                builder.store_reg(pointer, ll.IntType(32), "r10")
                builder.branch(end)

                pointer = builder.load_reg(ll.IntType(32), "r10")
                mem_size = builder.load_reg(ll.IntType(32), "r12")
                cond = builder.icmp_signed("<=",mem_size,pointer)
                builder.cbranch(cond, add_memory_block, no_add_memory_block)
            case Token.MOVE_LEFT:
                pointer = builder.load_reg(ll.IntType(32), "r10")
                builder.sub(pointer,ll.Constant(ll.IntType(32), 4))
            case Token.INCREMENT:
                pointer = builder.load_reg(ll.IntType(32), "r10")
                ptr = builder.load(builder.gep(pointer,stack_base))
                builder.add(ptr,ll.Constant(ll.IntType(32),1))
                builder.store(ptr,builder.gep(stack_base,pointer))
            case Token.DECREMENT:
                pointer = builder.load_reg(ll.IntType(32),"r10")
                builder.
                ptr = builder.load(builder.gep(stack_base,pointer))
                builder.sub(ptr,ll.Constant(ll.IntType(32),1))
                builder.store(ptr,builder.gep(stack_base,pointer))
            case Token.STDOUT:
                pointer = builder.load_reg(ll.IntType(32),"r10")
                builder.ptrtoint()
                builder.inttoptr()
                builder.call(putchar,builder.gep(stack_base,pointer))
                pass
            case Token.STDINT:
                print("VOU SUPORTAR ESSA PORRA NAO FODASE")
                raise ValueError("FODASE")
            case Token.LOOP_OPEN:
                cond = entry.append_basic_block()
                body = entry.append_basic_block()
                end = entry.append_basic_block()
                builder.branch(cond)
                builder.position_at_end(cond)
                pointer = builder.load_reg(ll.IntType(32),"r10")
                value = builder.load(builder.gep(pointer,stack_base))
                cmp = builder.icmp_signed("==",value,ll.Constant(ll.IntType(32),0))
                builder.cbranch(cmp,end,body)
                builder.position_at_end(body)
                loops_blocks.append(WhileBlock(cond,body,end))
            case Token.LOOP_CLOSE:
                loop = loops_blocks.pop()
                builder.branch(loop.cond)
                builder.position_at_end(loop.end)

    strmod = str(mod)

    llmod = llvm.parse_assembly(strmod)
    print(llmod)

def bytecode_compiler(code:str) -> list[Instruction]:
    token_code: list[Instruction] = []
    loop_head:  list[Instruction] = []
    for i,c in enumerate(filter(lambda x: x in (">","<","+","-",".",",","[","]") , code)):
        match c:
            case ">":
                token_code.append(Instruction(Token.MOVE_RIGHT,i))
            case "<":
                token_code.append(Instruction(Token.MOVE_LEFT,i))
            case "+":
                token_code.append(Instruction(Token.INCREMENT,i))
            case "-":
                token_code.append(Instruction(Token.DECREMENT,i))
            case ".":
                token_code.append(Instruction(Token.STDOUT,i))
            case ",":
                token_code.append(Instruction(Token.STDINT,i))
            case "[":
                tok = Instruction(Token.LOOP_OPEN,i)
                loop_head.append(tok)
                token_code.append(tok)
            case "]":
                corresponding_open = loop_head.pop()
                closing = Instruction(Token.LOOP_CLOSE,i, corresponding_open)
                corresponding_open.optional = closing
                token_code.append(closing)
    # print(token_code)
    # token_code = bytecode_optimizer(token_code)

    return token_code

def bytecode_optimizer(code:list[Instruction]) -> list[Instruction]:
    instruction_pointer = 0
    while instruction_pointer < len(code):
        base: Instruction = code[instruction_pointer]
        if not base.token_type in OPTMIZABLE:
            instruction_pointer += 1
            continue
        while 1:
            if base.token_type == code[instruction_pointer+1].token_type:
                base.times+= 1
                code.remove(code[instruction_pointer+1])
            else:
                break
        print(f"removed {base.token_type} {base.times}")
        instruction_pointer += 1

    return code

def run_bytecode(code:list[Instruction]):
    instruction_pointer = 0
    memory = [0]
    pointer = 0
    while instruction_pointer < len(code):
        c = code[instruction_pointer]
        match c.token_type:
            case Token.MOVE_RIGHT:
                pointer += 1
                if pointer >= len(memory):
                    memory.append(0)
            case Token.MOVE_LEFT:
                pointer -= 1
            case Token.INCREMENT:
                memory[pointer] += 1
            case Token.DECREMENT:
                memory[pointer] -= 1
            case Token.STDOUT:
                if memory[pointer] in range(110000):
                    sys.stdout.write(chr(memory[pointer]))
                    sys.stdout.flush()
                else:
                    print(memory[pointer])
            case Token.STDINT:
                memory[pointer] = bytes(sys.stdin.read(1))[0]
            case Token.LOOP_OPEN:
                if not memory[pointer]:
                    instruction_pointer = c.optional.index
            case Token.LOOP_CLOSE:
                if memory[pointer]:
                    instruction_pointer = c.optional.index
        instruction_pointer += 1

def run_optimized_bytecode(code:list[Instruction]):
    instruction_pointer = 0
    memory = [0]
    pointer = 0
    while instruction_pointer < len(code):
        c = code[instruction_pointer]
        match c.token_type:
            case Token.MOVE_RIGHT:
                pointer += c.times
                if pointer >= len(memory):
                    memory += [0] * c.times
            case Token.MOVE_LEFT:
                pointer -= c.times
            case Token.INCREMENT:
                memory[pointer] += c.times
            case Token.DECREMENT:
                memory[pointer] -= c.times
            case Token.STDOUT:
                if memory[pointer] in range(110000):
                    sys.stdout.write(chr(memory[pointer]))
                    sys.stdout.flush()
                else:
                    print(memory[pointer])
            case Token.STDINT:
                memory[pointer] = bytes(sys.stdin.read(1))[0]
            case Token.LOOP_OPEN:
                if not memory[pointer]:
                    instruction_pointer = code.index(c.optional) 
            case Token.LOOP_CLOSE:
                if memory[pointer]:
                    instruction_pointer = code.index(c.optional) 
        instruction_pointer += 1
    print(f"{instruction_pointer}")
    print("END")
def run(code:str):
    memory = [0]
    pointer = 0
    open_loop_pointer = []
    instruction_pointer =0 
    while instruction_pointer < len(code):
        c = code[instruction_pointer]
        add = True
        match c:
            case ">":
                pointer += 1
                if pointer >= len(memory):
                    memory.append(0)
            case "<":
                pointer -= 1
            case "+":
                memory[pointer] += 1
            case "-":
                memory[pointer] -= 1
            case ".":
                sys.stdout.write(chr(memory[pointer]))
                sys.stdout.flush()
            case ",":
                memory[pointer] = bytes(sys.stdin.read(1))[0]
            case "[":
                if memory[pointer]:
                    open_loop_pointer.append(instruction_pointer)
                else:
                    instruction_pointer = code.index("]",instruction_pointer) +1
                    add = False
            case "]":
                if memory[pointer]:
                    instruction_pointer = open_loop_pointer.pop()
                    add = False
                else:
                    open_loop_pointer.pop()
        if add:
            instruction_pointer += 1


code = open(sys.argv[1],"r").read()
print("compiling to bytecode...")
com = bytecode_compiler(code)
print("trasnpiling to assembly...")
asm = bytecode_to_assembly(com)
open("test.asm","w").write(asm)
#run_bytecode(com)