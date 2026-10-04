with open('mainyapayzeka1.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# İlk def main() satırını bul (2668. satır yaklaşık)
first_main_idx = None
for i, line in enumerate(lines):
    if 'def main():' in line:
        first_main_idx = i
        break

# if __name__ satırını bul
ifname_idx = None
for i, line in enumerate(lines):
    if 'if __name__' in line:
        ifname_idx = i
        break

# İlk olandan if __name__'ye kadar olan hattları sil (eski main())
# Ve ikinci def main() ile devam et
if first_main_idx is not None and ifname_idx is not None:
    # Eski main() sil (first_main_idx'den söylü if __name__'ye kadar)
    new_lines = lines[:first_main_idx] + lines[ifname_idx:]
    
    with open('mainyapayzeka1.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f'✅ Dosya düeltildi! Eski main() kaldırıldı.')
    print(f'✅ Dosya satır sayısı: {len(new_lines)}')
else:
    print('❌ Hata: main() veya __name__ bulunamadı')
