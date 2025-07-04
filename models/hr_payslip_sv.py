from odoo import models, fields, api
from datetime import datetime
import io
import base64
import csv

class HrPayslipSV(models.Model):
    _name = 'hr.payslip.sv'
    _description = 'Planilla SV'
    _order = 'date_start desc'

    name = fields.Char(string='Nombre', compute='_compute_name', store=True)
    date_start = fields.Date(string='Fecha Inicio', required=True, default=fields.Date.today)
    date_end = fields.Date(string='Fecha Fin', required=True)
    period_type = fields.Selection([
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual')
    ], string='Tipo de Periodo', required=True)

    line_ids = fields.One2many('hr.payslip.sv.line', 'payslip_id', string='Líneas de Planilla')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Finalizado'),
    ], string='Estado', default='draft')

    archivo_spu = fields.Binary("Archivo SPU", readonly=True)
    nombre_archivo_spu = fields.Char("Nombre Archivo", readonly=True)

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.name = f"Planilla {rec.date_start.strftime('%d/%m/%Y')} - {rec.date_end.strftime('%d/%m/%Y')}"
            else:
                rec.name = 'Nueva Planilla'

    def action_calcular_planilla(self):
        self.ensure_one()
        self.line_ids.unlink()
        empleados = self.env['hr.employee'].search([
            ('contract_id.state', '=', 'open')
        ])
        for emp in empleados:
            contrato = emp.contract_id
            if contrato and contrato.wage:
                self.env['hr.payslip.sv.line'].create({
                    'payslip_id': self.id,
                    'employee_id': emp.id,
                    'wage': contrato.wage,
                })

    def action_marcar_finalizado(self):
        for rec in self:
            rec.state = 'done'

    def action_exportar_spu(self):
        salida = io.StringIO()
        writer = csv.writer(salida)
        writer.writerow([
            'DUI/NIT del Empleador',
            'Número patronal ISSS',
            'Período Mes-Año',
            'Correlativo Centro de Trabajo ISSS',
            'Número de Documento',
            'Tipo de Documento',
            'Número de Afiliación ISSS',
            'Institución Previsional',
            'Primer Nombre',
            'Segundo Nombre',
            'Primer Apellido',
            'Segundo Apellido',
            'Apellido de Casada',
            'Salario',
            'Pago Adicional',
            'Monto de Vacación',
            'Días',
            'Horas',
            'Días de Vacación',
            'Código de Observación 01',
            'Código de Observación 02'
        ])
        for linea in self.line_ids:
            emp = linea.employee_id
            contrato = emp.contract_id
            if not contrato:
                continue
            nombres = emp.name.split()
            primer_nombre = nombres[0] if len(nombres) > 0 else ''
            segundo_nombre = nombres[1] if len(nombres) > 1 else ''
            apellidos = emp.name.split()
            primer_apellido = apellidos[-1] if len(apellidos) >= 1 else ''
            segundo_apellido = apellidos[-2] if len(apellidos) >= 2 else ''
            writer.writerow([
                '038931211', '789897899', self.date_end.strftime('%m%Y'), '456',
                emp.dui.replace('-', '') if emp.dui else '',
                '01', (emp.nup or '').zfill(9), 'COF',
                primer_nombre, segundo_nombre,
                segundo_apellido, primer_apellido,
                '', f"{linea.wage:.2f}", "0.00", "0.00", "30", "160", "0", "00", "00"
            ])
        datos_csv = salida.getvalue().encode('utf-8')
        salida.close()
        nombre = f'planilla_spu_{self.date_end.strftime("%Y%m")}.csv'
        self.write({
            'archivo_spu': base64.b64encode(datos_csv),
            'nombre_archivo_spu': nombre,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=hr.payslip.sv&id={self.id}&field=archivo_spu&filename_field=nombre_archivo_spu&download=true',
            'target': 'self',
        }

    def action_exportar_planilla_csv(self):
        self.ensure_one()
        salida = io.StringIO()
        writer = csv.writer(salida)
        writer.writerow([
            'Empleado', 'Sueldo Base', 'Salario Diario', 'Salario Hora', 'Días Laborados',
            'Horas Extras Diurnas', 'Horas Extras Nocturnas', 'Horas Extras Festivos',
            'Bonificaciones', 'Comisiones', 'Viáticos', 'Otros Ingresos', 'Total Ingresos',
            'ISSS', 'AFP', 'Renta', 'Embargos', 'Anticipos', 'Otras Deducciones',
            'Total Descuentos', 'Neto a Pagar',
            'Horas Trabajadas', 'Vacaciones Acumuladas', 'Aguinaldo Acumulado',
            'Indemnización', 'Bono Vacacional', 'Días Incapacidad', 'Días Licencia',
            'Estado de Pago', 'Forma de Pago', 'Observaciones'
        ])
        for linea in self.line_ids:
            writer.writerow([
                linea.employee_id.name,
                linea.wage, linea.salario_diario, linea.salario_hora, linea.dias_laborados,
                linea.horas_extras_diurnas, linea.horas_extras_nocturnas, linea.horas_extras_festivos,
                linea.bonificaciones, linea.comisiones, linea.viaticos, linea.otros_ingresos, linea.total_ingresos,
                linea.isss, linea.afp, linea.renta, linea.embargos, linea.anticipos, linea.otras_deducciones,
                linea.total_descuentos, linea.neto_pagar,
                linea.horas_trabajadas, linea.vacaciones_acumuladas, linea.aguinaldo_acumulado,
                linea.indemnizacion, linea.bono_vacacional, linea.dias_incapacidad, linea.dias_licencia,
                linea.estado_pago, linea.forma_pago, linea.observaciones
            ])
        datos = salida.getvalue().encode('utf-8')
        salida.close()
        nombre = f'planilla_interna_{self.date_end.strftime("%Y%m")}.csv'
        self.write({
            'archivo_spu': base64.b64encode(datos),
            'nombre_archivo_spu': nombre,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=hr.payslip.sv&id={self.id}&field=archivo_spu&filename_field=nombre_archivo_spu&download=true',
            'target': 'self',
        }

