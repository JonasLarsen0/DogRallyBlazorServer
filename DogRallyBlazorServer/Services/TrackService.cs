using DogRallyBlazorServer.Data;
using DogRallyBlazorServer.Models.Responses;
using DogRallyBlazorServer.Models.DTOs;
using Microsoft.EntityFrameworkCore;
using DogRallyBlazorServer.Models;

namespace DogRallyBlazorServer.Services;

public interface ITrackService
{
    Task<GetAllTracksResponse> GetTracks();
    Task<BaseResponse> AddTrack(AddTrackForm form);

}
public class TrackService : ITrackService
{
    private readonly IDbContextFactory<DataContext> _factory;

    public TrackService(IDbContextFactory<DataContext> factory)
    {
        _factory = factory;
    }

    public async Task<BaseResponse> AddTrack(AddTrackForm form)
    {
        var response = new BaseResponse();
        try
        {
            using (var context = _factory.CreateDbContext())
            {
                context.Add(new Track
                {
                    CreatorName = form.CreatorName,
                    Date = form.Date,
                    JudgeName = form.JudgeName,
                    PlaceName = form.PlaceName,
                    TrackImg = form.TrackImg,
                    RallyClass = form.RallyClass
                });
                var result = await context.SaveChangesAsync();

                if (result == 1)
                {
                    response.StatusCode = 200;
                    response.Message = "Bane tilføjet";
                }
                else
                {
                    response.StatusCode = 400;
                    response.Message = "Der opstod et problem med at tilføje banen";
                }
            }
        }
        catch (Exception ex)
        {
            response.StatusCode = 500;
            response.Message = "Problemer med at tilføje banen:" + ex.Message;
        }
        return response;
    }

    public async Task<GetAllTracksResponse> GetTracks()
    {
        var response = new GetAllTracksResponse();

        try
        {
            using (var context = _factory.CreateDbContext())
            {
                var tracks = await context.Tracks.ToListAsync();
                response.Tracks = tracks;
                response.StatusCode = 200;
                response.Message = "Success";
            }
        }
        catch (Exception ex)
        {
            response.StatusCode = 500;
            response.Message = "Problemer med at hente banerne:" + ex.Message;
            response.Tracks = null;
        }

        return response;
    }
}

