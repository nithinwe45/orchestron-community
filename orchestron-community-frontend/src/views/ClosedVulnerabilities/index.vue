<template>
    <div>
        <b-container fluid>
            <b-card>
                <p class="title">Closed Vulnerabilities by Severity</p>
                <hr>
                <br>
                <b-row>
                    <b-col sm="8" class="m2-top">
                        <p class="text-left">
                            <span class="vul-count">
                            {{ totalVul }}
                            </span>
                        </p>
                    </b-col>
                    <b-col sm="4">
                        <v-select  :options="selectOption"
                            v-model="selectedOption"
                            v-on:input="onInput(selectedOption)">
                        </v-select>
                    </b-col>
                </b-row>
                <br>
                <vul-progress-bar
                    :high="highCount"
                    :medium="mediumCount"
                    :low="lowCount"
                    :info="infoCount"
                    :total="totalVul"></vul-progress-bar>
                <br>
                <closed-vul-table :dataItems="items" :pageNumberCount="totalVul"></closed-vul-table>
            </b-card>
        </b-container>
    </div>
</template>
<script>
import ClosedVulTable from '@/components/ClosedVulnerability/ClosedVulTable.vue'
import VulProgressBar from '@/components/OpenVulnerabilities/VulProgressBar'
import axios from '@/utils/auth'
import { notValidUser } from '@/utils/checkAuthUser'

export default {
  name: 'OpenVulnerabilities',
  components: {
    ClosedVulTable,
    VulProgressBar
  },
  data() {
    return {
      items: [],
      totalVul: 0,
      highCount: 0,
      mediumCount: 0,
      lowCount: 0,
      infoCount: 0,
      selectOption: ['Default View', 'Show False Positives'],
      selectedOption: 'Default View'
    }
  },
  created() {
    this.org = localStorage.getItem('org')
    this.token = localStorage.getItem('token')
    this.fetchDataOpenVul()
  },
  methods: {
    fetchDataOpenVul() {
      if (this.org && this.token) {
        axios.get('/closedvul/org/' + this.org + '/?true=1')
          .then(res => {
            for (const val of Object.values(res.data.results)) {
              if (val.severity === 3) {
                this.highCount += 1
              } else if (val.severity === 2) {
                this.mediumCount += 1
              } else if (val.severity === 1) {
                this.lowCount += 1
              } else if (val.severity === 0) {
                this.infoCount += 1
              } else {
                this.infoCount += 1
              }
              const splitVuls = val.names.split(',')
              const cwe = val.cwe
              const sev = val.severity
              const openFor = val.open_for
              const tool = val.tools
              let commonName = ''
              let vulName = ''
              let appName = ''
              const multipleVuls = {}
              for (const actualVul of splitVuls) {
                const vulDetail = actualVul.split('###')
                vulName = vulDetail[0]
                appName = vulDetail[1]
                if (splitVuls.length > 2) {
                  multipleVuls[vulName] = appName
                }
              }
              if (val.common_name === null) {
                commonName = vulName
              } else {
                commonName = val.common_name
              }
              const checkObjectEmpty = Object.keys(multipleVuls).length === 0
              if (checkObjectEmpty) {
                this.items.push({
                  cwe: cwe,
                  sev: sev,
                  openFor: openFor,
                  commonName: commonName,
                  name: multipleVuls,
                  app: appName,
                  tool: tool,
                  multiple: false,
                  vulName: vulName
                })
              } else {
                this.items.push({
                  cwe: cwe,
                  sev: sev,
                  openFor: openFor,
                  commonName: commonName,
                  name: multipleVuls,
                  app: appName,
                  tool: tool,
                  multiple: true,
                  vulName: vulName
                })
              }
            }
            this.totalVul = res.data.count
          }).catch(error => {
            if (error.res.status === 404) {
              this.$router.push('/not_found')
            } else if (error.res.status === 403) {
              this.$router.push('/forbidden')
            } else {
              this.$router.push('/error')
            }
          })
      } else {
        notValidUser()
        this.$router.push('/')
      }
    },
    onInput(value) {
      if (value === 'Default View') {
        if (this.org && this.token) {
          axios.get('/closedvul/org/' + this.org + '/?true=1')
            .then(res => {
              this.items = []
              this.totalVul = 0
              this.highCount = 0
              this.mediumCount = 0
              this.lowCount = 0
              this.infoCount = 0
              for (const val of Object.values(res.data.results)) {
                if (val.severity === 3) {
                  this.highCount += 1
                } else if (val.severity === 2) {
                  this.mediumCount += 1
                } else if (val.severity === 1) {
                  this.lowCount += 1
                } else if (val.severity === 0) {
                  this.infoCount += 1
                } else {
                  this.infoCount += 1
                }
                const splitVuls = val.names.split(',')
                const cwe = val.cwe
                const sev = val.severity
                const openFor = val.open_for
                const tool = val.tools
                let commonName = ''
                let vulName = ''
                let appName = ''
                const multipleVuls = {}
                for (const actualVul of splitVuls) {
                  const vulDetail = actualVul.split('###')
                  vulName = vulDetail[0]
                  appName = vulDetail[1]
                  if (splitVuls.length > 2) {
                    multipleVuls[vulName] = appName
                  }
                }
                if (val.common_name === null) {
                  commonName = vulName
                } else {
                  commonName = val.common_name
                }
                const checkObjectEmpty = Object.keys(multipleVuls).length === 0
                if (checkObjectEmpty) {
                  this.items.push({
                    cwe: cwe,
                    sev: sev,
                    openFor: openFor,
                    commonName: commonName,
                    name: multipleVuls,
                    app: appName,
                    tool: tool,
                    multiple: false,
                    vulName: vulName
                  })
                } else {
                  this.items.push({
                    cwe: cwe,
                    sev: sev,
                    openFor: openFor,
                    commonName: commonName,
                    name: multipleVuls,
                    app: appName,
                    tool: tool,
                    multiple: true,
                    vulName: vulName
                  })
                }
              }
              this.totalVul = res.data.count
            }).catch(error => {
              if (error.res.status === 404) {
                this.$router.push('/not_found')
              } else if (error.res.status === 403) {
                this.$router.push('/forbidden')
              } else {
                this.$router.push('/error')
              }
            })
        } else {
          notValidUser()
          this.$router.push('/')
        }
      } else {
        if (this.org && this.token) {
          axios.get('/closedvul/org/' + this.org + '/?false=1')
            .then(res => {
              if (res.status === 200) {
                this.items = []
                this.totalVul = 0
                this.highCount = 0
                this.mediumCount = 0
                this.lowCount = 0
                this.infoCount = 0
                for (const val of Object.values(res.data.results)) {
                  if (val.severity === 3) {
                    this.highCount += 1
                  } else if (val.severity === 2) {
                    this.mediumCount += 1
                  } else if (val.severity === 1) {
                    this.lowCount += 1
                  } else if (val.severity === 0) {
                    this.infoCount += 1
                  } else {
                    this.infoCount += 1
                  }
                  const splitVuls = val.names.split(',')
                  const cwe = val.cwe
                  const sev = val.severity
                  const openFor = val.open_for
                  const tool = val.tools
                  let commonName = ''
                  let vulName = ''
                  let appName = ''
                  const multipleVuls = {}
                  for (const actualVul of splitVuls) {
                    const vulDetail = actualVul.split('###')
                    vulName = vulDetail[0]
                    appName = vulDetail[1]
                    if (splitVuls.length > 2) {
                      multipleVuls[vulName] = appName
                    }
                  }
                  if (val.common_name === null) {
                    commonName = vulName
                  } else {
                    commonName = val.common_name
                  }
                  const checkObjectEmpty = Object.keys(multipleVuls).length === 0
                  if (checkObjectEmpty) {
                    this.items.push({
                      cwe: cwe,
                      sev: sev,
                      openFor: openFor,
                      commonName: commonName,
                      name: multipleVuls,
                      app: appName,
                      tool: tool,
                      multiple: false,
                      vulName: vulName
                    })
                  } else {
                    this.items.push({
                      cwe: cwe,
                      sev: sev,
                      openFor: openFor,
                      commonName: commonName,
                      name: multipleVuls,
                      app: appName,
                      tool: tool,
                      multiple: true,
                      vulName: vulName
                    })
                  }
                }
                this.totalVul = res.data.count
              } else {
                this.$router.push('/forbidden')
              }
            }).catch(error => {
              if (error.res.status === 404) {
                this.$router.push('/not_found')
              } else if (error.res.status === 403) {
                this.$router.push('/forbidden')
              } else {
                this.$router.push('/error')
              }
            })
        } else {
          notValidUser()
          this.$router.push('/')
        }
      }
    }
  }
}
</script>
<style scoped>
  .vul-count{
    font-family: 'Avenir';
    color: #25231F;
    font-size: 48px;
    font-weight: 200;
    line-height: 0.33;
  }
</style>
