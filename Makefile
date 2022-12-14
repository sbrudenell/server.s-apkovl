BIN=$(CURDIR)/bin
APKOVL=$(BIN)/server.apkovl.tar.gz
APKOVL_SRC=$(CURDIR)/apkovl
IPXE_CFG=$(CURDIR)/ipxe.cfg
BOOT_CFG=$(CURDIR)/boot.cfg
IPXE_INNER=ipxe/src/bin-x86_64-efi/ipxe.efi
IPXE=$(CURDIR)/ipxe/$(IPXE_INNER)
ESP=$(BIN)/esp.img
EMULATE_PY=$(CURDIR)/emulate.py
BIOS=/usr/share/ovmf/OVMF.fd

all: $(ESP)

release: $(IPXE) $(APKOVL) $(IPXE_CFG) $(BOOT_CFG)

emulate: $(ESP)
	$(EMULATE_PY) -bios $(BIOS) -drive if=virtio,file=$(ESP),format=raw -smbios type=3,asset=local-test

emulate_prod: $(ESP)
	$(EMULATE_PY) -bios $(BIOS) -drive if=virtio,file=$(ESP),format=raw

submodules:
	git submodule update --init --recursive

update:
	git submodule foreach git pull origin master

$(IPXE): submodules
	$(MAKE) -C ipxe $(IPXE_INNER)

$(APKOVL): $(shell find $(APKOVL_SRC) -type f)
	mkdir -p $(dir $(APKOVL))
	# special permissions
	chmod 700 $(APKOVL_SRC)/root
	chmod 700 $(APKOVL_SRC)/root/.ssh
	chmod 600 $(APKOVL_SRC)/root/.ssh/authorized_keys
	tar --owner=0 --group=0 -c -v -z -p -C $(APKOVL_SRC) . -f $(APKOVL)

$(ESP): $(IPXE) $(IPXE_CFG) $(BOOT_CFG) $(APKOVL)
	mkdir -p $(dir $(ESP))
	dd if=/dev/zero of=$(ESP) bs=1M count=64
	mkfs.vfat $(ESP) -F 32
	mmd -i $(ESP) ::/EFI
	mmd -i $(ESP) ::/EFI/BOOT
	mcopy -i $(ESP) $(IPXE) ::/EFI/BOOT/BOOTX64.EFI
	mcopy -i $(ESP) $(IPXE_CFG) ::/EFI/BOOT/IPXE.CFG
	mcopy -i $(ESP) $(BOOT_CFG) ::/EFI/BOOT/BOOT.CFG
	mcopy -i $(ESP) $(APKOVL) ::/$(notdir $(APKOVL))

.PHONY: emulate submodules $(IPXE)
