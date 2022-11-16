nextflow.enable.dsl=2

params.ser = "FLASH_PILOT_2A"

params.HOME = "${params.SCRATCH_ROOT}"
params.DATA = "${params.SCRATCH_ROOT}/data/${params.ser}/"
params.CATALOGUE = "${params.SCRATCH_ROOT}/data/${params.ser}/catalogue/"
params.NOISE = "${params.SCRATCH_ROOT}/data/${params.ser}/noise/"
params.SOURCEFITS = "${params.SCRATCH_ROOT}/data/${params.ser}/sourceSpectra/"
params.OUTPUTS = "${params.SCRATCH_ROOT}/outputs/${param.ser}/"
params.OUTPUT_PLOTS = "${params.SCRATCH_ROOT}/outputs/${param.ser}/spectral_plots/"
params.OUTPUT_LINEFINDER = "${params.SCRATCH_ROOT}/outputs/${param.ser}/ascii_files/"
params.OUTPUT_LOGS = "${params.SCRATCH_ROOT}/outputs/${param.ser}/logs/"


process setup {

    input:
        val ser

    output:
        val ser, emit ser_output

    script:
        """

        #!/bin/bash

        mkdir -p ${params.CATALOGUE} 
        mkdir -p ${params.NOISE} 
        mkdir -p ${params.SOURCEFITS} 
        mkdir -p ${params.OUTPUT_PLOTS} 
        mkdir -p ${params.OUTPUT_LINEFINDER} 
        mkdir -p ${params.OUTPUT_LOGS} 
        """
}

workflow flash_ser {
	take:
		ser

	main:
		setup(ser)

	// Download image data
	get_sched_blocks(setup.out.ser_output)
	casda_download(get_sched_blocks.out.obs_list)

	// Create spectral plots and ascii files for linefinder
	make_spectral_plots(casda_download.out.sbid_list)

	// Run linefinder
	

workflow {
	main:
		flash_ser(params.ser)
}
