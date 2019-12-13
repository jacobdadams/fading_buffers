import arcpy
import os
import sys

def progbar(progress, total, postfix=''):
    '''
    Simple output for reporting progress given current progress value and progress value at completion
    '''
    done = int(50 * progress / total)
    percent = round(100 * progress / total, 2)
    sys.stdout.write('\r[{}{}] {}% {}'.format('#' * done, '_' * (50 - done), percent, postfix))
    sys.stdout.flush()

def multibuffers(in_fc, out_fc, distances, inner=False):

    field_name = 'distance'

    describe_input = arcpy.Describe(in_fc)

    arcpy.CreateFeatureclass_management(os.path.dirname(out_fc), os.path.basename(out_fc), 'POLYGON', spatial_reference=describe_input.spatialReference)
    arcpy.AddField_management(out_fc, field_name, 'DOUBLE')

    #: Get the original geometry
    dissolved_fc = arcpy.Dissolve_management(in_fc, 'memory\\diss_fc')[0]
    with arcpy.da.SearchCursor(dissolved_fc, 'SHAPE@') as dissolved_cursor:
        for row in dissolved_cursor:
            dissolved_original = row[0]
            break

    #: Fade around the outside
    if not inner:
        with arcpy.da.SearchCursor(in_fc, 'SHAPE@') as search_cursor:
            for row in search_cursor:
                feature = row[0]

                #: Make a buffer for each one (dual-sided, nothing removed)
                #: Densify or risk small gaps
                buffers = [feature.buffer(i).densify('DISTANCE', i/10, 0.1) for i in distances]

                total = len(buffers)

                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', field_name]) as out_rows:
                    for i, buff in enumerate(buffers):
                        progbar(i, total)
                        # If it's the first, just difference the original
                        if not i:
                            out_feature = buff.difference(dissolved_original)

                        #: Otherwise, difference the previous buffer and the original
                        else:
                            out_feature = buff.difference(buffers[i-1]).difference(dissolved_original)

                        out_rows.insertRow([out_feature, distances[i]])

    #: Inner fade
    else:

        #: Add one more step for removing the inside area
        step = distances[-1] - distances[-2]
        distances.append(distances[-1] + step)
        #: Invert and reverse distances
        distances = [-i for i in distances[::-1]]

        total = int(arcpy.GetCount_management(in_fc)[0])

        with arcpy.da.SearchCursor(in_fc, 'SHAPE@') as search_cursor:
            row_counter = 0
            for row in search_cursor:

                progbar(row_counter, total)
                feature = row[0]

                #: Make a buffer for each one (dual-sided, nothing removed)
                #: Densify or risk small gaps
                buffers = [feature.buffer(i).densify('DISTANCE', i/10, 0.1) for i in distances]

                # total = len(buffers)

                with arcpy.da.InsertCursor(out_fc, ['SHAPE@', field_name]) as out_rows:
                    for i, buff in enumerate(buffers):
                        
                        # progbar(i, total)

                        if not i:
                            # out_feature = buff#.difference(dissolved_original)
                            inner_feature = buff
                        else:
                            out_feature = buff.difference(buffers[i-1])

                            out_rows.insertRow([out_feature, distances[i]])
                
                row_counter += 1

source_feature_class = r'c:\gis\Projects\Terrain\Terrain.gdb\Munis'
output_dir = r'c:\gis\Projects\Terrain\Terrain.gdb'

width = 300
steps = 20
step_width = int(width/steps)

output_name = 'Munis_buffers{}x{}inner'.format(width, steps)
output_path = os.path.join(output_dir, output_name)

inner = True

# if inner:
#     distances = [-i for i in range(0, width, step_width)]
# else:
#     distances = [i for i in range(0, width, step_width)]

distances = [i for i in range(0, width, step_width)]

#: Call method from arcpy source
multibuffers(source_feature_class, output_path, distances, inner)

#: Call arcpy method
# # arcpy.MultipleRingBuffer_analysis(source_feature_class, output_path, distances, Outside_Polygons_Only='OUTSIDE_ONLY')

# arcpy.MultipleRingBuffer_analysis(source_feature_class, output_path, distances, Dissolve_Option= 'NONE', Outside_Polygons_Only='OUTSIDE_ONLY')

# # arcpy.MultipleRingBuffer_analysis(source_feature_class, output_path, distances)
