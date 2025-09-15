# AMD GPU Optimization Guide
# ========================

## Seu Sistema: AMD RX 5700 (Detectada ✅)

### Status Atual
- **GPU**: AMD Radeon RX 5700 (4GB VRAM)
- **PyTorch**: CPU version (funcional)
- **AI Assistant**: ✅ Operacional em CPU
- **Performance**: Moderada (CPU-bound)

## Opções de Otimização

### 1. 🔥 **MELHOR PERFORMANCE** - ROCm (Linux/WSL2)
```bash
# No Ubuntu/WSL2:
sudo apt update
sudo apt install rocm-dev
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.4.2
```
**Vantagens**: 
- GPU nativa (até 10x mais rápido)
- Acesso aos 4GB de VRAM
- Suporte completo ao modelo BioMistral

**Desvantagens**: 
- Requer Linux ou WSL2
- Configuração mais complexa

### 2. 🚀 **BOA PERFORMANCE** - DirectML (Windows Nativo)
```bash
pip install torch-directml
# Modifica provider para usar DirectML
```
**Vantagens**: 
- Funciona no Windows
- Usa GPU AMD
- Fácil instalação

**Desvantagens**: 
- Performance menor que ROCm
- Suporte limitado de modelos

### 3. ✅ **ATUAL** - CPU Otimizado (Windows)
```bash
# Já configurado e funcionando
pip install torch torchvision torchaudio
```
**Vantagens**: 
- Funciona imediatamente
- Compatível com todos os modelos
- Estável e confiável

**Desvantagens**: 
- Não usa a GPU
- Performance limitada

## Recomendações Específicas para RX 5700

### Para Máxima Performance:
1. **Use WSL2 + ROCm**: Melhor opção para sua GPU
2. **Configure BioMistral completo**: Com GPU terá acesso ao modelo médico completo
3. **8GB+ RAM**: Para modelos maiores

### Para Facilidade (Atual):
1. **Mantenha CPU**: Sistema já otimizado e funcional
2. **Use modelos menores**: Como o atual DialoGPT-small
3. **Configure cloud fallback**: OpenAI como backup

## Scripts de Instalação

### ROCm (WSL2/Linux):
```bash
# Execute dentro do WSL2:
curl -fsSL https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian/ ubuntu main' | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt update
sudo apt install rocm-dev python3-pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.4.2
```

### DirectML (Windows):
```bash
pip uninstall torch torchvision torchaudio
pip install torch-directml
# Ajustar provider para DirectML
```

## Benchmarks Esperados (RX 5700)

- **CPU**: ~2-5 tokens/segundo
- **DirectML**: ~8-15 tokens/segundo  
- **ROCm**: ~20-40 tokens/segundo
- **vLLM+ROCm**: ~50-100 tokens/segundo

## Status do Sistema

Seu sistema está **perfeitamente configurado** para:
✅ Detecção automática de GPU AMD
✅ Fallback inteligente para CPU
✅ Configurações otimizadas para RX 5700
✅ Pronto para upgrade futuro para ROCm

---
**Próximo Passo Recomendado**: Configurar WSL2 + ROCm para 10x performance boost
